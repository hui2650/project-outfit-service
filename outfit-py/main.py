from __future__ import annotations

import io, os, asyncio, time, hashlib
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from PIL import Image
import traceback

import httpx
import torch
import numpy as np
from transformers import CLIPProcessor, CLIPModel

# ================= ENV =================
from dotenv import load_dotenv
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ================= CONFIG =================
MODEL_NAME = "openai/clip-vit-base-patch32"

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ✅ Kakao(Daum) Image Search (K-fashion domain boost)
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
SEARCH_SOURCES = [s.strip().lower() for s in os.getenv("SEARCH_SOURCES", "naver,kakao").split(",") if s.strip()]

# ✅ full-body gates
PORTRAIT_AR_MIN = 1.02
BBOX_FEET_Y_MIN = 0.86

# ✅ quality
MIN_SHORT_SIDE = 480

# ✅ item presence gate
ITEM_REGION_MIN_PROB = 0.20
ITEM_REGION_MARGIN_MIN = 0.02
ITEM_VS_PRODUCT_MIN = 0.025  # wearing vs product min margin

# ✅ color strictness
COLOR_STRICT_DEFAULT = True
COLOR_STRICT_IF_CONF_GE = 0.45
COLOR_FALLBACK_COMPAT = True

# ✅ pose gate (soft by default)
POSE_GATE_STRICT = False
POSE_GATE_PENALTY = 0.10

# ✅ screenshot/product gate
OUTFIT_BAD_MARGIN = 0.00
OUTFIT_ABS_MIN = 0.52

MAX_CONCURRENCY = 6
FINAL_LIMIT_DEFAULT = 8

# ✅ scoring stabilization
MARGIN_GOOD = 0.08
PENALTY_LOW_MARGIN = 0.08
PENALTY_LOW_TBEST = 0.06

# ⚠️ IMPORTANT: shape score easily biases footwear toward sneakers in lookbooks.
# Keep it, but DISABLE for footwear by default.
SHAPE_MIN = 0.18
SHAPE_WEIGHT = 0.08

# ✅ cache by image bytes (Swagger file-sticky mitigation)
CACHE_TTL_SEC = 180
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

# ================= APP =================
app = FastAPI(title="Styling Recommend API")

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    print("\n=== UNHANDLED ERROR ===")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": repr(exc)})

# ================= MODELS =================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("[BOOT] device =", device)

clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

from ultralytics import YOLO
yolo_person = YOLO("yolov8n.pt")
yolo_pose = YOLO("yolov8n-pose.pt")

# rembg
try:
    from rembg import remove as rembg_remove
    REMBG_OK = True
except Exception:
    REMBG_OK = False


# ================= UTILS =================
def pil_rgb(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert("RGB")

def clamp(v, a, b):
    return max(a, min(b, v))

def looks_like_image_contenttype(ct: str) -> bool:
    ct = (ct or "").lower()
    return ct.startswith("image/")

def safe_crop(img: Image.Image, x1: float, y1: float, x2: float, y2: float) -> Image.Image:
    w, h = img.size
    x1 = int(clamp(int(x1), 0, w - 1))
    y1 = int(clamp(int(y1), 0, h - 1))
    x2 = int(clamp(int(x2), x1 + 1, w))
    y2 = int(clamp(int(y2), y1 + 1, h))
    return img.crop((x1, y1, x2, y2))

def center_square_crop(img: Image.Image, ratio: float = 0.85) -> Image.Image:
    w, h = img.size
    side = int(min(w, h) * ratio)
    cx, cy = w // 2, h // 2
    x1 = cx - side // 2
    y1 = cy - side // 2
    x2 = x1 + side
    y2 = y1 + side
    return safe_crop(img, x1, y1, x2, y2)

def short_side(img: Image.Image) -> int:
    return min(img.size[0], img.size[1])

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ================= CLIP =================
@torch.no_grad()
def clip_scores(img: Image.Image, prompts: List[str]) -> List[float]:
    inp = clip_processor(text=prompts, images=img, return_tensors="pt", padding=True)
    inp = {k: v.to(device) for k, v in inp.items()}
    out = clip_model(**inp)
    probs = out.logits_per_image.softmax(dim=1)[0]
    return probs.cpu().tolist()

@torch.no_grad()
def get_img_features(img: Image.Image) -> torch.Tensor:
    """
    Safe image feature extraction (avoids BaseModelOutputWithPooling norm issues)
    """
    inp = clip_processor(images=img, return_tensors="pt")
    pixel_values = inp["pixel_values"].to(device)

    feats = None
    try:
        feats = clip_model.get_image_features(pixel_values=pixel_values)
    except Exception:
        feats = None

    if feats is None or not torch.is_tensor(feats):
        vision_out = clip_model.vision_model(pixel_values=pixel_values)
        pooled = vision_out.pooler_output
        feats = clip_model.visual_projection(pooled)

    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


# ================= COLOR (rembg + LAB) =================
COLOR_KOR = {
    "beige": "베이지",
    "black": "검정",
    "white": "흰색",
    "navy": "네이비",
    "gray": "회색",
    "brown": "브라운",
}

def rgb_to_lab_image(img_rgb: Image.Image) -> np.ndarray:
    lab = img_rgb.convert("LAB")
    return np.asarray(lab, dtype=np.float32)

def lab_prototypes() -> Dict[str, np.ndarray]:
    proto_rgb = {
        "black": (15, 15, 15),
        "white": (245, 245, 245),
        "gray":  (160, 160, 160),
        "beige": (210, 190, 155),
        "brown": (120, 85, 55),
        "navy":  (25, 40, 85),
    }
    out = {}
    for k, rgb in proto_rgb.items():
        p = Image.new("RGB", (1, 1), rgb)
        out[k] = rgb_to_lab_image(p).reshape(3)
    return out

LAB_PROTOS = lab_prototypes()

def rembg_alpha(img_rgb: Image.Image) -> np.ndarray:
    if not REMBG_OK:
        raise RuntimeError("rembg 미설치/로드 실패 (pip install rembg onnxruntime)")
    buf = io.BytesIO()
    img_rgb.save(buf, format="PNG")
    out_bytes = rembg_remove(buf.getvalue())
    out_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    alpha = np.asarray(out_img.split()[-1], dtype=np.float32) / 255.0
    return alpha

def dominant_color_label_rembg_lab(img_rgb: Image.Image) -> Tuple[str, float]:
    a = rembg_alpha(img_rgb)
    lab = rgb_to_lab_image(img_rgb)

    fg = a > 0.35
    if fg.sum() < 80:
        img2 = center_square_crop(img_rgb, 0.80)
        lab2 = rgb_to_lab_image(img2)
        med = np.median(lab2.reshape(-1, 3), axis=0)
    else:
        med = np.median(lab[fg].reshape(-1, 3), axis=0)

    dists = {k: float(np.linalg.norm(med - p)) for k, p in LAB_PROTOS.items()}
    best = min(dists, key=dists.get)
    conf = float(clamp(1.0 - dists[best] / 60.0, 0.0, 1.0))
    return best, conf

def color_compatible(user_color: str, cand_color: str) -> bool:
    u = (user_color or "").lower().strip()
    c = (cand_color or "").lower().strip()
    if not u or not c:
        return False
    if u == c:
        return True
    neutral = {"black", "white", "gray", "beige", "brown", "navy"}
    if u in {"white", "black", "gray"}:
        return c in neutral
    if u == "beige":
        return c in {"beige", "brown", "white", "gray"}
    if u == "brown":
        return c in {"brown", "beige", "black", "navy"}
    if u == "navy":
        return c in {"navy", "black", "gray", "white"}
    return False

def robust_color_from_crops(crops: List[Image.Image]) -> Tuple[str, float]:
    votes = defaultdict(float)
    for c in crops[:6]:
        try:
            lab, cf = dominant_color_label_rembg_lab(c)
            votes[lab] += float(cf)
        except Exception:
            continue
    if not votes:
        return ("", 0.0)
    best = max(votes.items(), key=lambda kv: kv[1])[0]
    conf = float(clamp(votes[best] / max(1.0, sum(votes.values())), 0.0, 1.0))
    return best, conf


# ================= YOLO PERSON + POSE FULLBODY =================
def yolo_best_person_bbox(img: Image.Image) -> Tuple[Optional[Tuple[float, float, float, float]], int]:
    r = yolo_person.predict(img, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None, 0

    boxes = r.boxes.xyxy.cpu().numpy()
    cls = r.boxes.cls.cpu().numpy()

    persons = [i for i, c in enumerate(cls) if int(c) == 0]
    if not persons:
        return None, 0

    best_i = max(persons, key=lambda k: (boxes[k][2] - boxes[k][0]) * (boxes[k][3] - boxes[k][1]))
    x1, y1, x2, y2 = boxes[best_i]
    return (float(x1), float(y1), float(x2), float(y2)), len(persons)

def bbox_fullbody_and_feet(img: Image.Image) -> Tuple[bool, Dict[str, Any]]:
    w, h = img.size
    bbox, person_count = yolo_best_person_bbox(img)
    if bbox is None:
        return False, {"person_count": 0}

    x1, y1, x2, y2 = bbox
    person_h = (y2 - y1) / max(1, h)
    top_ratio = y1 / max(1, h)
    bottom_ratio = y2 / max(1, h)

    full_ok = person_h >= 0.70
    feet_ok = bottom_ratio >= BBOX_FEET_Y_MIN
    head_ok = top_ratio <= 0.15
    multi_ok = (person_count == 1)

    ok = (full_ok and feet_ok and head_ok and multi_ok)

    return ok, {
        "person_h": float(person_h),
        "top_ratio": float(top_ratio),
        "bottom_ratio": float(bottom_ratio),
        "full_ok": int(full_ok),
        "feet_ok": int(feet_ok),
        "head_ok": int(head_ok),
        "multi_ok": int(multi_ok),
        "person_count": int(person_count),
        "bbox": [float(x1), float(y1), float(x2), float(y2)],
    }

def pose_fullbody_gate(img: Image.Image) -> Tuple[bool, Dict[str, Any]]:
    w, h = img.size
    r = yolo_pose.predict(img, verbose=False)[0]
    if r.keypoints is None or len(r.keypoints) == 0:
        return False, {"pose": "no_keypoints"}

    xy = r.keypoints.xy.cpu().numpy()
    conf = r.keypoints.conf.cpu().numpy()
    n = xy.shape[0]

    def area_of(i: int) -> float:
        pts = xy[i]; c = conf[i]
        m = c > 0.2
        if m.sum() < 4:
            return 0.0
        p = pts[m]
        return float((p[:,0].max()-p[:,0].min())*(p[:,1].max()-p[:,1].min()))

    best_i = max(range(n), key=area_of)
    pts = xy[best_i]
    cfs = conf[best_i]

    if cfs[0] <= 0.20:
        return False, {"pose": "nose_missing"}
    la_ok = cfs[15] > 0.20
    ra_ok = cfs[16] > 0.20
    if not (la_ok or ra_ok):
        return False, {"pose": "ankle_missing"}

    nose_y = float(pts[0,1] / max(1, h))
    ankle_y = float((max(pts[15,1], pts[16,1]) if (la_ok and ra_ok) else (pts[15,1] if la_ok else pts[16,1])) / max(1, h))

    head_ok = nose_y <= 0.22
    feet_ok = ankle_y >= 0.90
    ok = head_ok and feet_ok

    return ok, {"nose_y": round(nose_y,4), "ankle_y": round(ankle_y,4), "head_ok": int(head_ok), "feet_ok": int(feet_ok)}

def crop_region_by_part(person_crop: Image.Image, part: str) -> Image.Image:
    w, h = person_crop.size
    part = part or "torso"

    if part == "head":
        return safe_crop(person_crop, 0, h*0.00, w, h*0.25)
    if part == "upper":
        return safe_crop(person_crop, 0, h*0.12, w, h*0.55)
    if part == "lower":
        return safe_crop(person_crop, 0, h*0.45, w, h*0.95)
    if part == "feet":
        return safe_crop(person_crop, 0, h*0.70, w, h*1.00)
    if part == "hands":
        return safe_crop(person_crop, 0, h*0.25, w, h*0.85)
    return safe_crop(person_crop, 0, h*0.12, w, h*0.85)

def multi_crops_for_part(person_crop: Image.Image, part: str) -> List[Image.Image]:
    w, h = person_crop.size
    crops: List[Image.Image] = []
    crops.append(crop_region_by_part(person_crop, part))

    if part == "feet":
        crops.append(safe_crop(person_crop, 0, h*0.62, w, h*1.00))
        crops.append(safe_crop(person_crop, w*0.08, h*0.65, w*0.92, h*1.00))
        crops.append(safe_crop(person_crop, w*0.15, h*0.68, w*0.85, h*1.00))
    elif part == "hands":
        crops.append(safe_crop(person_crop, 0, h*0.18, w, h*0.95))
        crops.append(safe_crop(person_crop, w*0.05, h*0.15, w*0.95, h*0.92))
        crops.append(safe_crop(person_crop, w*0.12, h*0.20, w*0.88, h*0.92))
    elif part == "upper":
        crops.append(safe_crop(person_crop, 0, h*0.06, w, h*0.65))
        crops.append(safe_crop(person_crop, w*0.06, h*0.10, w*0.94, h*0.62))
        crops.append(safe_crop(person_crop, w*0.12, h*0.12, w*0.88, h*0.60))
    elif part == "lower":
        crops.append(safe_crop(person_crop, 0, h*0.38, w, h*1.00))
        crops.append(safe_crop(person_crop, w*0.06, h*0.45, w*0.94, h*0.98))
        crops.append(safe_crop(person_crop, w*0.12, h*0.48, w*0.88, h*0.98))
    else:
        crops.append(safe_crop(person_crop, 0, h*0.08, w, h*0.95))

    # center fallback
    crops.append(center_square_crop(person_crop, 0.72))

    out: List[Image.Image] = []
    for c in crops:
        if short_side(c) >= 160:
            out.append(c)
    return out


# ================= TAXONOMY =================
OPEN_FOOTWEAR = {"sandals", "slippers", "slides", "flip flops"}
CLOSED_FOOTWEAR = {"sneakers", "boots", "loafers", "dress shoes"}

ITEM_TAXONOMY: List[Dict[str, Any]] = [
    # footwear
    {"en": "sneakers",     "kr": ["운동화", "스니커즈"], "part": "feet", "yolo_classes": []},
    {"en": "boots",        "kr": ["부츠"],             "part": "feet", "yolo_classes": []},
    {"en": "loafers",      "kr": ["로퍼"],             "part": "feet", "yolo_classes": []},
    {"en": "dress shoes",  "kr": ["구두", "드레스슈즈"], "part": "feet", "yolo_classes": []},
    {"en": "sandals",      "kr": ["샌들"],             "part": "feet", "yolo_classes": []},
    {"en": "slippers",     "kr": ["슬리퍼"],           "part": "feet", "yolo_classes": []},
    {"en": "slides",       "kr": ["슬라이드"],         "part": "feet", "yolo_classes": []},
    {"en": "flip flops",   "kr": ["쪼리"],             "part": "feet", "yolo_classes": []},

    # tops
    {"en": "t-shirt",        "kr": ["티셔츠", "반팔"],     "part": "upper", "yolo_classes": []},
    {"en": "shirt",          "kr": ["셔츠"],               "part": "upper", "yolo_classes": []},
    {"en": "hoodie",         "kr": ["후드", "후드티"],     "part": "upper", "yolo_classes": []},
    {"en": "knit sweater",   "kr": ["니트", "스웨터"],     "part": "upper", "yolo_classes": []},
    {"en": "cardigan",       "kr": ["가디건"],             "part": "upper", "yolo_classes": []},

    # bottoms
    {"en": "jeans",        "kr": ["청바지", "데님"],     "part": "lower", "yolo_classes": []},
    {"en": "slacks",       "kr": ["슬랙스"],             "part": "lower", "yolo_classes": []},
    {"en": "shorts",       "kr": ["반바지"],             "part": "lower", "yolo_classes": []},
    {"en": "skirt",        "kr": ["치마", "스커트"],      "part": "lower", "yolo_classes": []},

    # outer
    {"en": "long coat",      "kr": ["롱코트", "코트"],       "part": "torso", "yolo_classes": []},
    {"en": "trench coat",    "kr": ["트렌치코트", "트렌치"], "part": "torso", "yolo_classes": []},
    {"en": "puffer jacket",  "kr": ["패딩", "푸퍼"],         "part": "torso", "yolo_classes": []},
    {"en": "blazer",         "kr": ["블레이저", "자켓"],     "part": "upper", "yolo_classes": []},

    # bags
    {"en": "backpack",      "kr": ["백팩", "배낭"],              "part": "hands", "yolo_classes": ["backpack"]},
    {"en": "handbag",       "kr": ["핸드백", "숄더백", "토트백"],  "part": "hands", "yolo_classes": ["handbag"]},
    {"en": "crossbody bag", "kr": ["크로스백"],                 "part": "hands", "yolo_classes": []},

    # head/accessories
    {"en": "hat",         "kr": ["모자", "캡"],         "part": "head",  "yolo_classes": []},
    {"en": "sunglasses",  "kr": ["선글라스"],           "part": "head",  "yolo_classes": []},
    {"en": "tie",         "kr": ["넥타이"],             "part": "upper", "yolo_classes": ["tie"]},
    {"en": "umbrella",    "kr": ["우산"],               "part": "hands", "yolo_classes": ["umbrella"]},
    {"en": "watch",       "kr": ["시계"],               "part": "hands", "yolo_classes": []},
]

def taxonomy_prompts_with_map() -> Tuple[List[str], List[int]]:
    """
    Feet items get multiple prompts to reduce 'formal outfit => dress shoes' bias.
    """
    prompts: List[str] = []
    idx_map: List[int] = []

    for i, x in enumerate(ITEM_TAXONOMY):
        en = x["en"]
        if x.get("part") == "feet":
            prompts.append(f"a photo of feet wearing {en}")
            idx_map.append(i)
            prompts.append(f"feet wearing {en}, open toe visible" if en in OPEN_FOOTWEAR else f"a person wearing {en}")
            idx_map.append(i)
        else:
            prompts.append(f"a photo of {en}")
            idx_map.append(i)

    return prompts, idx_map

def taxonomy_best(user_crop: Image.Image) -> Tuple[Dict[str, Any], float]:
    prompts, idx_map = taxonomy_prompts_with_map()
    scores = clip_scores(user_crop, prompts)
    best_prompt_idx = int(torch.tensor(scores).argmax())
    item_idx = idx_map[best_prompt_idx]
    best_item = ITEM_TAXONOMY[item_idx]
    best_prob = float(scores[best_prompt_idx])
    return best_item, best_prob


# ================= SHAPE / SILHOUETTE =================
def shape_prompts_for_item(item_en: str) -> List[str]:
    item_en = (item_en or "").lower().strip()
    if item_en in ("long coat", "trench coat", "puffer jacket", "blazer"):
        return [
            "a long coat outfit photo", "a short coat outfit photo",
            "a trench coat outfit photo", "a blazer outfit photo",
            "a puffer jacket outfit photo",
            "an oversized fit outfit", "a slim fit outfit",
        ]
    if item_en in ("jeans", "slacks", "shorts", "skirt"):
        return [
            "wide fit pants outfit", "straight fit pants outfit", "skinny fit pants outfit",
            "slacks outfit", "jeans outfit",
        ]
    if item_en in CLOSED_FOOTWEAR or item_en in OPEN_FOOTWEAR:
        # Footwear shape prompt tends to bias to sneakers; keep minimal
        return ["footwear outfit photo", "casual outfit", "formal outfit"]
    return ["a full body street fashion outfit", "a casual outfit", "a formal outfit"]

def shape_score(person_crop: Image.Image, item_en: str) -> Tuple[float, str]:
    sp = shape_prompts_for_item(item_en)
    ss = clip_scores(person_crop, sp)
    best_i = int(torch.tensor(ss).argmax())
    best = float(ss[best_i])
    label = sp[best_i]
    return best, label


# ================= SEARCH =================
def korea_style_keywords() -> str:
    return "무신사 스냅 코디북 룩북 전신 착샷 스트릿 데일리 OOTD"

def build_negative_keywords(item_en: str, item_part: str) -> str:
    base = "-쇼핑 -가격 -구매 -판매 -광고 -쿠폰 -스토어 -공식 -상품 -리뷰 -택배 -문의 -재고 -뉴스 -기사 -연예 -화보"
    # For open footwear, sneakers noise is extremely common
    if item_part == "feet" and item_en in OPEN_FOOTWEAR:
        base += " -스니커즈 -운동화 -러닝화 -런닝화 -나이키 -아디다스 -뉴발란스 -조던"
    return base

async def naver_search_once(query: str, display: int = 80, start: int = 1) -> List[Dict[str, Any]]:
    url = "https://openapi.naver.com/v1/search/image"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": min(int(display), 100), "start": max(1, int(start)), "sort": "sim", "filter": "large"}

    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers=headers, params=params)
        print("[NAVER]", r.status_code, "| query =", query)
        if r.status_code != 200:
            print("[NAVER ERR]", r.text[:300])
            return []
        data = r.json()
        items = data.get("items", []) or []
        out = []
        for it in items:
            out.append({
                "link": it.get("link"),
                "originallink": it.get("originallink") or it.get("link"),
                "thumbnail": it.get("thumbnail") or it.get("link"),
                "title": it.get("title") or "",
                "source": "naver",
            })
        return out

async def kakao_search_once(query: str, size: int = 80, page: int = 1) -> List[Dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        return []
    url = "https://dapi.kakao.com/v2/search/image"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query, "size": min(int(size), 80), "page": max(1, int(page)), "sort": "accuracy"}

    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers=headers, params=params)
        print("[KAKAO]", r.status_code, "| query =", query)
        if r.status_code != 200:
            print("[KAKAO ERR]", r.text[:300])
            return []
        data = r.json()
        docs = data.get("documents", []) or []
        out = []
        for d in docs:
            out.append({
                "link": d.get("image_url"),
                "originallink": d.get("doc_url") or d.get("image_url"),
                "thumbnail": d.get("thumbnail_url") or d.get("image_url"),
                "title": d.get("display_sitename") or "",
                "source": "kakao",
            })
        return out

def merge_dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        link = it.get("link")
        if not link or link in seen:
            continue
        out.append(it)
        seen.add(link)
    return out

async def search_multi(queries: List[str], display_each: int = 80) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    all_items: List[Dict[str, Any]] = []
    per_source = defaultdict(int)

    for q in queries:
        if "naver" in SEARCH_SOURCES:
            ni = await naver_search_once(q, display=display_each, start=1)
            per_source["naver"] += len(ni)
            all_items.extend(ni)

        if "kakao" in SEARCH_SOURCES:
            ki = await kakao_search_once(q, size=min(display_each, 80), page=1)
            per_source["kakao"] += len(ki)
            all_items.extend(ki)

    merged = merge_dedupe(all_items)
    return merged, dict(per_source)


# ================= OPTIONAL YOLO OBJECT GATE =================
YOLO_NAMES = yolo_person.model.names if hasattr(yolo_person, "model") and hasattr(yolo_person.model, "names") else {}

def yolo_has_any(img: Image.Image, wanted_names: List[str]) -> bool:
    if not wanted_names:
        return True
    r = yolo_person.predict(img, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return False
    cls = r.boxes.cls.cpu().numpy().astype(int).tolist()
    present = set(YOLO_NAMES.get(i, "") for i in cls)
    return any(w in present for w in wanted_names)


# ================= PRESENCE PROMPTS =================
def choose_distractors(item_en: str, item_part: str) -> List[str]:
    item_en = (item_en or "").lower().strip()
    if "bag" in item_en or item_en in ("backpack", "handbag", "crossbody bag"):
        return ["handbag", "backpack", "tote bag", "crossbody bag", "suitcase"]

    if item_part == "feet":
        # ✅ crucial: open vs closed separation
        if item_en in OPEN_FOOTWEAR:
            return ["sneakers", "boots", "loafers", "dress shoes"]
        if item_en in CLOSED_FOOTWEAR:
            return ["sandals", "slippers", "slides", "flip flops"]
        return ["sneakers", "sandals", "boots", "loafers"]

    if item_part == "upper":
        return ["t-shirt", "shirt", "hoodie", "knit sweater", "jacket"]
    if item_part == "lower":
        return ["jeans", "slacks", "shorts", "skirt"]
    if item_part == "head":
        return ["hat", "sunglasses", "cap"]
    return ["clothing", "fashion item", "outfit", "product photo"]

def presence_prompts_strong(item_en: str, distractors: List[str]) -> List[str]:
    """
    Stronger separation:
    - wearing vs product
    - open footwear vs sneakers
    """
    item_en = (item_en or "").strip().lower()

    if item_en in OPEN_FOOTWEAR:
        targets = [
            f"feet wearing {item_en} open toe visible",
            f"a person wearing {item_en} open toe footwear",
            f"summer street style outfit wearing {item_en}",
            f"casual outfit with {item_en} on feet",
        ]
    else:
        targets = [
            f"a full body street fashion photo wearing {item_en}",
            f"a person wearing {item_en} in an outfit photo",
            f"street style outfit with {item_en}",
            f"{item_en} worn by a person in a full body outfit photo",
        ]

    product = [
        f"a product photo of {item_en}",
        f"a close-up product shot of {item_en}",
    ]

    dist = [f"a full body street fashion photo wearing {d}" for d in distractors[:4]]
    return targets + product + dist


# ================= FOOTWEAR TYPE GATE (fix sneakers leaking into slippers) =================
@torch.no_grad()
def footwear_type_gate(foot_crop: Image.Image) -> Dict[str, float]:
    prompts = [
        # open-toe
        "open toe footwear",
        "visible toes",
        "sandals on feet",
        "slippers on feet",
        "slides on feet",
        "flip flops on feet",
        # closed
        "sneakers on feet",
        "running shoes on feet",
        "boots on feet",
        "loafers on feet",
        "dress shoes on feet",
    ]
    s = clip_scores(foot_crop, prompts)
    keys = ["open", "toes", "sandals", "slippers", "slides", "flipflops",
            "sneakers", "running", "boots", "loafers", "dress"]
    return {k: float(v) for k, v in zip(keys, s)}

def open_footwear_ok(foot_crop: Image.Image) -> Tuple[bool, Dict[str, float]]:
    sc = footwear_type_gate(foot_crop)
    open_best = max(sc["open"], sc["toes"], sc["sandals"], sc["slippers"], sc["slides"], sc["flipflops"])
    closed_best = max(sc["sneakers"], sc["running"], sc["boots"], sc["loafers"], sc["dress"])
    # ✅ Thresholds tuned to avoid over-dropping; only drop if clearly not open-toe
    ok = (open_best >= 0.18) and (open_best > closed_best + 0.02)
    meta = {
        "open_best": round(open_best, 4),
        "closed_best": round(closed_best, 4),
        "gap": round(open_best - closed_best, 4),
    }
    return ok, meta


# ================= MAIN =================
@app.post("/recommend/image")
async def recommend_image(
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    requestId: str = Form(...),
    textQuery: str = Form("")
):
    print("\n[REQ] HIT /recommend/image")
    print("[REQ] requestId=", requestId, "textQuery=", textQuery, "limit=", limit)
    print("[REQ] filename=", image.filename, "content_type=", image.content_type)

    if not NAVER_CLIENT_ID and "naver" in SEARCH_SOURCES:
        return {"error": "NAVER_CLIENT_ID 없음"}
    if not NAVER_CLIENT_SECRET and "naver" in SEARCH_SOURCES:
        return {"error": "NAVER_CLIENT_SECRET 없음"}
    if "kakao" in SEARCH_SOURCES and not KAKAO_REST_API_KEY:
        print("[WARN] SEARCH_SOURCES includes kakao but KAKAO_REST_API_KEY is missing -> kakao returns empty")
    if not REMBG_OK:
        return {"error": "rembg 미설치/로드 실패 (pip install rembg onnxruntime 필요)"}

    img_bytes = await image.read()
    cache_key = sha256_bytes(img_bytes) + f":{(textQuery or '').strip()}:{limit}"
    now = time.time()

    if cache_key in _CACHE:
        ts, payload = _CACHE[cache_key]
        if now - ts <= CACHE_TTL_SEC:
            payload["debug"]["cache"] = {"hit": True, "ttl_sec": CACHE_TTL_SEC}
            return payload
        else:
            _CACHE.pop(cache_key, None)

    user_img = pil_rgb(img_bytes)
    user_q = (textQuery or "").strip()

    drop_counts = defaultdict(int)
    drop_lock = asyncio.Lock()
    async def drop(reason: str):
        async with drop_lock:
            drop_counts[reason] += 1

    # 0) user mode
    user_person_bbox, user_person_count = yolo_best_person_bbox(user_img)
    if user_person_bbox is not None and user_person_count >= 1:
        user_person_crop = safe_crop(user_img, *user_person_bbox)
        user_base_for_clip = user_person_crop
        user_mode = "person_wearing"
    else:
        user_person_crop = None
        user_base_for_clip = center_square_crop(user_img, 0.85)
        user_mode = "item_only"

    # 1) taxonomy
    best_item, best_prob = taxonomy_best(user_base_for_clip)
    item_en = best_item["en"]
    item_kr_list = best_item["kr"]
    item_part = best_item["part"]
    yolo_gate_classes = best_item.get("yolo_classes", [])

    # 2) user item crops/features
    if user_person_crop is not None:
        user_item_crops = multi_crops_for_part(user_person_crop, item_part)
        user_item_crop = user_item_crops[0]
    else:
        user_item_crops = [center_square_crop(user_img, 0.85)]
        user_item_crop = user_item_crops[0]

    user_color, user_color_conf = robust_color_from_crops(user_item_crops)
    user_item_features = get_img_features(user_item_crop)

    # 3) queries
    color_kor = COLOR_KOR.get(user_color, "")
    item_kor = item_kr_list[0] if item_kr_list else "패션"
    neg = build_negative_keywords(item_en=item_en, item_part=item_part)
    ko_kw = korea_style_keywords()

    q1 = f"{color_kor} {item_kor} {ko_kw} {user_q} {neg}".strip()
    q2 = f"{color_kor} {item_kor} 전신 착용샷 코디 스트릿 {user_q} {neg}".strip()
    q3 = f"{item_kor} {ko_kw} {user_q} {neg}".strip()
    q4 = f"{item_kor} 전신 코디 착샷 룩북 {user_q} {neg}".strip()
    queries = [q1, q2, q3, q4]

    cand_items, per_source_raw = await search_multi(queries, display_each=80)

    if len(cand_items) < 70:
        q5 = f"{item_kor} 무신사 스냅 전신 코디 {neg}".strip()
        q6 = f"{item_kor} 코디북 전신 착샷 OOTD {neg}".strip()
        more, more_raw = await search_multi([q5, q6], display_each=80)
        cand_items = merge_dedupe(cand_items + more)
        for k, v in more_raw.items():
            per_source_raw[k] = per_source_raw.get(k, 0) + v
        queries = queries + [q5, q6]

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    # 4) candidate processing
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:

        async def process(it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with sem:
                try:
                    url = it.get("link")
                    if not url:
                        await drop("no_url")
                        return None

                    try:
                        r = await client.get(url)
                    except Exception:
                        await drop("download_fail")
                        return None

                    if r.status_code != 200:
                        await drop("download_fail")
                        return None

                    ct = r.headers.get("content-type", "")
                    if not looks_like_image_contenttype(ct):
                        await drop("not_image_contenttype")
                        return None

                    try:
                        img = pil_rgb(r.content)
                    except Exception:
                        await drop("decode_fail")
                        return None

                    if short_side(img) < MIN_SHORT_SIDE:
                        await drop("too_small")
                        return None

                    # full-body bbox
                    ok_bbox, bbox = bbox_fullbody_and_feet(img)
                    if not ok_bbox:
                        await drop("bbox_fullbody_fail")
                        return None

                    # pose full-body (soft)
                    ok_pose, pose_meta = pose_fullbody_gate(img)
                    if POSE_GATE_STRICT and (not ok_pose):
                        await drop("pose_fullbody_fail")
                        return None

                    # screenshot/product gate
                    gate_prompts = [
                        "a full body street fashion outfit photo",
                        "a product photo of an item",
                        "a close-up product shot",
                        "a screenshot of a shopping webpage with lots of text",
                        "a collage of product images",
                        "a news photo with text overlay",
                    ]
                    gs = clip_scores(img, gate_prompts)
                    outfit_score = float(gs[0])
                    bad_score = float(max(gs[1:]))

                    if not (outfit_score > bad_score + OUTFIT_BAD_MARGIN and outfit_score >= OUTFIT_ABS_MIN):
                        await drop("screenshot_or_product")
                        return None

                    pb = bbox.get("bbox")
                    if not pb:
                        await drop("bbox_missing")
                        return None
                    person_crop = safe_crop(img, pb[0], pb[1], pb[2], pb[3])

                    # optional YOLO object gate
                    if yolo_gate_classes:
                        if not yolo_has_any(person_crop, yolo_gate_classes):
                            await drop("yolo_object_missing")
                            return None

                    # item presence gate (multi-crop best-of)
                    crops = multi_crops_for_part(person_crop, item_part)
                    distractors = choose_distractors(item_en, item_part)
                    prompts = presence_prompts_strong(item_en, distractors)

                    best = None
                    for c in crops:
                        rs = clip_scores(c, prompts)
                        t_best = float(max(rs[0:4]))
                        p_best = float(max(rs[4:6]))
                        margin_vs_product = float(t_best - p_best)
                        srt = sorted(rs, reverse=True)
                        margin_12 = float(srt[0] - srt[1]) if len(srt) >= 2 else 0.0
                        score_local = 0.75 * t_best + 0.25 * margin_vs_product

                        if (best is None) or (score_local > best["score_local"]):
                            best = {
                                "score_local": score_local,
                                "t_best": t_best,
                                "p_best": p_best,
                                "margin_vs_product": margin_vs_product,
                                "margin_12": margin_12,
                                "crop": c,
                            }

                    if best is None:
                        await drop("item_crop_fail")
                        return None

                    if best["t_best"] < ITEM_REGION_MIN_PROB:
                        await drop("item_region_low")
                        return None
                    if best["margin_12"] < ITEM_REGION_MARGIN_MIN:
                        await drop("item_region_ambiguous")
                        return None
                    if best["margin_vs_product"] < ITEM_VS_PRODUCT_MIN:
                        await drop("item_vs_product_ambiguous")
                        return None

                    cand_item_crop = best["crop"]

                    # ✅ NEW: footwear type gate (prevents sneakers leaking into slippers)
                    open_meta = None
                    if item_part == "feet" and item_en in OPEN_FOOTWEAR:
                        ok_open, open_meta = open_footwear_ok(cand_item_crop)
                        if not ok_open:
                            await drop("not_open_footwear")
                            return None

                    # robust color (use multiple crops)
                    cand_color, cand_color_conf = robust_color_from_crops([cand_item_crop] + crops)

                    strict_allowed = (user_color_conf >= COLOR_STRICT_IF_CONF_GE) and (cand_color_conf >= COLOR_STRICT_IF_CONF_GE)
                    strict_color_ok = (cand_color == user_color) if user_color else False
                    compat_color_ok = color_compatible(user_color, cand_color) if user_color else False

                    if COLOR_STRICT_DEFAULT:
                        if strict_allowed:
                            if not strict_color_ok:
                                await drop("color_strict_mismatch")
                                return None
                        else:
                            if COLOR_FALLBACK_COMPAT:
                                if not (strict_color_ok or compat_color_ok):
                                    await drop("color_compat_mismatch")
                                    return None
                            else:
                                if not strict_color_ok:
                                    await drop("color_strict_mismatch")
                                    return None

                    # similarity
                    cand_item_features = get_img_features(cand_item_crop)
                    visual_sim = float((user_item_features @ cand_item_features.T).item())

                    # portrait-ish score
                    ar = img.height / max(1, img.width)
                    ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.90

                    # style score (optional)
                    style_score = 0.0
                    if user_q:
                        style_prompts = [
                            f"a full body {user_q} outfit photo",
                            f"a {user_q} street fashion lookbook",
                            f"a fashion style of {user_q}",
                        ]
                        style_scores = clip_scores(person_crop, style_prompts)
                        style_score = float(max(style_scores))

                    # shape score (DISABLED for footwear to avoid sneaker bias)
                    sh_score = 0.0
                    sh_label = ""
                    if item_part != "feet":
                        sh_score, sh_label = shape_score(person_crop, item_en)
                        if sh_score < SHAPE_MIN:
                            sh_score = 0.0

                    # score stabilization
                    m = float(best["margin_vs_product"])
                    m_norm = clamp(m / MARGIN_GOOD, 0.0, 1.0)

                    penalty = 0.0
                    if m < 0.02:
                        penalty += PENALTY_LOW_MARGIN
                    if best["t_best"] < 0.22:
                        penalty += PENALTY_LOW_TBEST

                    score = (
                        0.50 * visual_sim +
                        0.24 * float(best["t_best"]) +
                        0.10 * m_norm +
                        0.08 * style_score +
                        (SHAPE_WEIGHT * float(sh_score) if item_part != "feet" else 0.0) +
                        0.04 * ar_score +
                        0.04 * float(bbox.get("person_h", 0.0))
                    ) - penalty

                    if not ok_pose:
                        score -= POSE_GATE_PENALTY

                    title = (it.get("title") or "").replace("<b>", "").replace("</b>", "")
                    landing = it.get("originallink") or url
                    thumb = it.get("thumbnail") or url

                    return {
                        "imageUrl": url,
                        "landingUrl": landing,
                        "thumbUrl": thumb,
                        "title": title,
                        "source": it.get("source", "unknown"),
                        "score": clamp(score, 0, 2),
                        "meta": {
                            "user_mode": user_mode,
                            "detected_item_en": item_en,
                            "detected_item_kr": item_kor,
                            "detected_item_prob": round(best_prob, 4),
                            "item_part": item_part,
                            "yolo_gate_classes": yolo_gate_classes,
                            "user_color": user_color,
                            "user_color_conf": round(float(user_color_conf), 4),
                            "cand_color": cand_color,
                            "cand_color_conf": round(float(cand_color_conf), 4),
                            "strict_allowed": int(strict_allowed),
                            "strict_color_ok": int(strict_color_ok),
                            "compat_color_ok": int(compat_color_ok),
                            "presence": {
                                "t_best": round(float(best["t_best"]), 4),
                                "p_best": round(float(best["p_best"]), 4),
                                "margin_vs_product": round(float(best["margin_vs_product"]), 4),
                                "margin_12": round(float(best["margin_12"]), 4),
                                "m_norm": round(float(m_norm), 4),
                                "penalty": round(float(penalty), 4),
                            },
                            "open_footwear_gate": open_meta,
                            "shape": {"score": round(float(sh_score), 4), "best_label": sh_label},
                            "visual_sim": round(visual_sim, 4),
                            "bbox": bbox,
                            "pose": pose_meta,
                            "gate_scores": {"outfit": round(outfit_score,4), "bad": round(bad_score,4)},
                        }
                    }

                except Exception:
                    await drop("process_exception")
                    return None

        processed = await asyncio.gather(*[process(it) for it in cand_items])

    items = [x for x in processed if x]
    items.sort(key=lambda x: x["score"], reverse=True)
    final = items[:limit]

    for idx, it in enumerate(final, start=1):
        it["rank"] = idx

    payload = {
        "requestId": requestId,
        "items": final,
        "debug": {
            "cache": {"hit": False, "ttl_sec": CACHE_TTL_SEC},
            "sources": {"enabled": SEARCH_SOURCES, "raw_per_source": per_source_raw},
            "detected": {
                "user_mode": user_mode,
                "item_en": item_en,
                "item_kr": (item_kr_list[0] if item_kr_list else ""),
                "item_prob": round(best_prob, 4),
                "user_color": user_color,
                "user_color_conf": round(float(user_color_conf), 4),
                "queries": queries,
                "yolo_gate_classes": yolo_gate_classes,
                "part": item_part,
                "pose_gate_strict": POSE_GATE_STRICT,
                "outfit_bad_margin": OUTFIT_BAD_MARGIN,
                "outfit_abs_min": OUTFIT_ABS_MIN,
                "min_short_side": MIN_SHORT_SIDE,
                "item_vs_product_min": ITEM_VS_PRODUCT_MIN,
                "color_strict_if_conf_ge": COLOR_STRICT_IF_CONF_GE,
                "shape_min": SHAPE_MIN,
                "shape_weight": SHAPE_WEIGHT,
                "footwear_gate_enabled": (item_part == "feet" and item_en in OPEN_FOOTWEAR),
            },
            "rawCount": len(cand_items),
            "passCount": len(items),
            "finalCount": len(final),
            "drop_counts": dict(sorted(drop_counts.items(), key=lambda kv: kv[1], reverse=True)),
        }
    }

    _CACHE[cache_key] = (now, payload)
    return payload

# run:
# python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug
