from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import io
import asyncio
import traceback
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, Optional, List, Tuple

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from PIL import Image

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

# Kakao optional
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

# ✅ Full-body gates
PORTRAIT_AR_MIN = 1.02
BBOX_FEET_Y_MIN = 0.86
PERSON_H_MIN = 0.70
HEAD_TOP_MAX = 0.15
MULTI_PERSON_MAX = 1

# ✅ item gate
ITEM_REGION_MIN_PROB = 0.20
ITEM_REGION_MARGIN_MIN = 0.02
ITEM_VS_PRODUCT_MIN_MARGIN = 0.03

# ✅ pose gate
POSE_GATE_STRICT = False
POSE_GATE_PENALTY = 0.10

# ✅ screenshot/product gate
OUTFIT_BAD_MARGIN = 0.00
OUTFIT_ABS_MIN = 0.52

# ✅ speed
MAX_CONCURRENCY = 6
FINAL_LIMIT_DEFAULT = 8

# ✅ Speed: cap candidate pool early
RAW_POOL_LIMIT = 220   # process at most this many raw links after merge

# ✅ CLIP speed: resize before inference
CLIP_MAX_SIDE = 640    # max side for CLIP inference (smaller=faster)

MIN_SHORT_SIDE = 480

# ✅ 색상
COLOR_STRICT_DEFAULT = True
COLOR_FALLBACK_COMPAT = True
COLOR_STRICT_IF_CONF_GE = 0.45  # strict only when both user & cand confidence high

# 빠른 RGB 프로토타입(1차)
FAST_COLOR_MAX_DIST = 85.0  # bigger => looser; tune 70~95

# Kakao / Naver query sizes
NAVER_DISPLAY_EACH = 80
KAKAO_SIZE_EACH = 80

# ================= APP =================
app = FastAPI(title="Styling Recommend API (Naver + Kakao)")

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

def short_side(img: Image.Image) -> int:
    return min(img.size[0], img.size[1])

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

# ================= CLIP =================
@torch.no_grad()
def clip_scores(img: Image.Image, prompts: List[str]) -> List[float]:
    inp = clip_processor(text=prompts, images=img, return_tensors="pt", padding=True)
    inp = {k: v.to(device) for k, v in inp.items()}
    out = clip_model(**inp)
    probs = out.logits_per_image.softmax(dim=1)[0]
    return probs.cpu().tolist()

def resize_max_side(img: Image.Image, max_side: int) -> Image.Image:
    if not max_side or max_side <= 0:
        return img
    w, h = img.size
    m = max(w, h)
    if m <= max_side:
        return img
    scale = max_side / float(m)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    return img.resize((nw, nh), Image.BICUBIC)

@torch.no_grad()
def get_img_features(img: Image.Image) -> torch.Tensor:
    # ✅ speed: resize before CLIP (keeps aspect ratio)
    img = resize_max_side(img, CLIP_MAX_SIDE)

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

# ================= CLIP FAST (cached text embeddings) =================
_TEXT_TOK_CACHE: Dict[str, Dict[str, torch.Tensor]] = {}
_TEXT_FEAT_CACHE: Dict[str, torch.Tensor] = {}

@torch.no_grad()
def get_text_features_cached(prompt: str) -> torch.Tensor:
    p = prompt.strip()
    if p in _TEXT_FEAT_CACHE:
        return _TEXT_FEAT_CACHE[p]

    if p not in _TEXT_TOK_CACHE:
        tok = clip_processor.tokenizer([p], padding=True, truncation=True, return_tensors="pt")
        _TEXT_TOK_CACHE[p] = {k: v.cpu() for k, v in tok.items()}

    tok = {k: v.to(device) for k, v in _TEXT_TOK_CACHE[p].items()}

    try:
        tf = clip_model.get_text_features(**tok)
    except Exception:
        # fallback
        text_out = clip_model.text_model(**tok)
        pooled = text_out.pooler_output
        tf = clip_model.text_projection(pooled)

    tf = tf / tf.norm(dim=-1, keepdim=True)
    _TEXT_FEAT_CACHE[p] = tf
    return tf

@torch.no_grad()
def clip_scores_fast(img: Image.Image, prompts: List[str]) -> List[float]:
    img_feat = get_img_features(img)  # [1, d]
    tfs = torch.cat([get_text_features_cached(p) for p in prompts], dim=0)  # [n, d]
    scale = clip_model.logit_scale.exp() if hasattr(clip_model, "logit_scale") else 1.0
    logits = (img_feat @ tfs.T) * scale
    probs = logits.softmax(dim=1)[0]
    return probs.detach().cpu().tolist()

# ================= COLOR (rembg + LAB + fast RGB) =================
COLOR_LABELS = ["black", "white", "gray", "beige", "brown", "navy"]
COLOR_KOR = {
    "beige": "베이지",
    "black": "검정",
    "white": "흰색",
    "navy": "네이비",
    "gray": "회색",
    "brown": "브라운",
}

FAST_RGB_PROTOS = {
    "black": np.array([15, 15, 15], dtype=np.float32),
    "white": np.array([245, 245, 245], dtype=np.float32),
    "gray": np.array([160, 160, 160], dtype=np.float32),
    "beige": np.array([210, 190, 155], dtype=np.float32),
    "brown": np.array([120, 85, 55], dtype=np.float32),
    "navy": np.array([25, 40, 85], dtype=np.float32),
}

def rgb_to_lab_image(img_rgb: Image.Image) -> np.ndarray:
    lab = img_rgb.convert("LAB")
    return np.asarray(lab, dtype=np.float32)

def lab_prototypes() -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    for k, rgb in FAST_RGB_PROTOS.items():
        p = Image.new("RGB", (1, 1), tuple(int(x) for x in rgb.tolist()))
        out[k] = rgb_to_lab_image(p).reshape(3)
    return out

LAB_PROTOS = lab_prototypes()

def fast_rgb_color(img_rgb: Image.Image) -> Tuple[str, float]:
    img2 = center_square_crop(img_rgb, 0.80)
    arr = np.asarray(img2, dtype=np.float32).reshape(-1, 3)
    med = np.median(arr, axis=0)
    dists = {k: float(np.linalg.norm(med - p)) for k, p in FAST_RGB_PROTOS.items()}
    best = min(dists, key=dists.get)
    conf = float(clamp(1.0 - dists[best] / 120.0, 0.0, 1.0))
    return best, conf

def dominant_color_label_fast_lab(img_rgb: Image.Image) -> Tuple[str, float]:
    img2 = center_square_crop(img_rgb, 0.78)
    med = np.median(rgb_to_lab_image(img2).reshape(-1, 3), axis=0)
    dists = {k: float(np.linalg.norm(med - p)) for k, p in LAB_PROTOS.items()}
    best = min(dists, key=dists.get)
    conf = float(clamp(1.0 - dists[best] / 60.0, 0.0, 1.0))
    return best, conf

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
    """Accurate color: rembg fg median in LAB -> prototype distance (fallback to fast)."""
    if not REMBG_OK:
        return fast_rgb_color(img_rgb)

    try:
        a = rembg_alpha(img_rgb)
        lab = rgb_to_lab_image(img_rgb)

        fg = a > 0.35
        if fg.sum() < 80:
            img2 = center_square_crop(img_rgb, 0.80)
            med = np.median(rgb_to_lab_image(img2).reshape(-1, 3), axis=0)
        else:
            med = np.median(lab[fg].reshape(-1, 3), axis=0)

        dists = {k: float(np.linalg.norm(med - p)) for k, p in LAB_PROTOS.items()}
        best = min(dists, key=dists.get)
        conf = float(clamp(1.0 - dists[best] / 60.0, 0.0, 1.0))
        return best, conf
    except Exception:
        return fast_rgb_color(img_rgb)

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

def fast_color_distance_ok(user_color: str, cand_crop: Image.Image) -> bool:
    if not user_color:
        return True
    cand, _ = fast_rgb_color(cand_crop)
    if cand == user_color:
        return True
    return color_compatible(user_color, cand)

def color_confirm_prompts(item_en: str, user_color: str) -> List[str]:
    col = (user_color or "").strip()
    if not col:
        return []
    negatives = [c for c in COLOR_LABELS if c != col][:4]
    return [
        f"a photo of {col} {item_en}",
        f"a person wearing {col} {item_en}",
        *[f"a photo of {c} {item_en}" for c in negatives],
    ]

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
    i = max(persons, key=lambda k: (boxes[k][2] - boxes[k][0]) * (boxes[k][3] - boxes[k][1]))
    x1, y1, x2, y2 = boxes[i]
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

    full_ok = person_h >= PERSON_H_MIN
    feet_ok = bottom_ratio >= BBOX_FEET_Y_MIN
    head_ok = top_ratio <= HEAD_TOP_MAX
    multi_ok = (person_count <= MULTI_PERSON_MAX)

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
        pts = xy[i]
        c = conf[i]
        m = c > 0.2
        if m.sum() < 4:
            return 0.0
        p = pts[m]
        return float((p[:, 0].max() - p[:, 0].min()) * (p[:, 1].max() - p[:, 1].min()))

    best_i = max(range(n), key=area_of)
    pts = xy[best_i]
    cfs = conf[best_i]

    if cfs[0] <= 0.20:
        return False, {"pose": "nose_missing"}
    la_ok = cfs[15] > 0.20
    ra_ok = cfs[16] > 0.20
    if not (la_ok or ra_ok):
        return False, {"pose": "ankle_missing"}

    nose_y = float(pts[0, 1] / max(1, h))
    if la_ok and ra_ok:
        ankle_y = float(max(pts[15, 1], pts[16, 1]) / max(1, h))
    else:
        ankle_y = float((pts[15, 1] if la_ok else pts[16, 1]) / max(1, h))

    head_ok = nose_y <= 0.22
    feet_ok = ankle_y >= 0.90
    ok = head_ok and feet_ok
    return ok, {
        "nose_y": round(nose_y, 4),
        "ankle_y": round(ankle_y, 4),
        "head_ok": int(head_ok),
        "feet_ok": int(feet_ok),
    }

# ================= CATEGORY CROPS =================
def crop_region_by_part(person_crop: Image.Image, part: str) -> Image.Image:
    w, h = person_crop.size
    part = part or "torso"
    if part == "head":
        return safe_crop(person_crop, 0, h * 0.00, w, h * 0.25)
    if part == "upper":
        return safe_crop(person_crop, 0, h * 0.12, w, h * 0.55)
    if part == "lower":
        return safe_crop(person_crop, 0, h * 0.45, w, h * 0.95)
    if part == "feet":
        return safe_crop(person_crop, 0, h * 0.70, w, h * 1.00)
    if part == "hands":
        return safe_crop(person_crop, 0, h * 0.25, w, h * 0.85)
    return safe_crop(person_crop, 0, h * 0.12, w, h * 0.85)

def multi_crops_for_part(person_crop: Image.Image, part: str) -> List[Image.Image]:
    w, h = person_crop.size
    crops: List[Image.Image] = []

    crops.append(crop_region_by_part(person_crop, part))

    if part == "feet":
        crops.append(safe_crop(person_crop, 0, h * 0.62, w, h * 1.00))
        crops.append(safe_crop(person_crop, w * 0.08, h * 0.65, w * 0.92, h * 1.00))
    elif part == "hands":
        crops.append(safe_crop(person_crop, 0, h * 0.18, w, h * 0.95))
        crops.append(safe_crop(person_crop, w * 0.05, h * 0.15, w * 0.95, h * 0.92))
    elif part == "upper":
        crops.append(safe_crop(person_crop, 0, h * 0.05, w, h * 0.65))
        crops.append(safe_crop(person_crop, w * 0.06, h * 0.08, w * 0.94, h * 0.62))
    elif part == "lower":
        crops.append(safe_crop(person_crop, 0, h * 0.35, w, h * 1.00))
        crops.append(safe_crop(person_crop, w * 0.06, h * 0.42, w * 0.94, h * 0.98))
    else:
        crops.append(safe_crop(person_crop, 0, h * 0.05, w, h * 0.95))

    crops.append(center_square_crop(person_crop, 0.72))

    out = [c for c in crops if short_side(c) >= 160]
    return out

# ================= TAXONOMY (ANY ITEM) =================
ITEM_TAXONOMY: List[Dict[str, Any]] = [
    # shoes
    {"en": "sneakers", "kr": ["운동화", "스니커즈"], "part": "feet", "yolo_classes": []},
    {"en": "boots", "kr": ["부츠"], "part": "feet", "yolo_classes": []},
    {"en": "loafers", "kr": ["로퍼"], "part": "feet", "yolo_classes": []},
    {"en": "dress shoes", "kr": ["구두", "드레스슈즈"], "part": "feet", "yolo_classes": []},

    # tops
    {"en": "t-shirt", "kr": ["티셔츠", "반팔"], "part": "upper", "yolo_classes": []},
    {"en": "shirt", "kr": ["셔츠"], "part": "upper", "yolo_classes": []},
    {"en": "hoodie", "kr": ["후드", "후드티"], "part": "upper", "yolo_classes": []},
    {"en": "knit sweater", "kr": ["니트", "스웨터"], "part": "upper", "yolo_classes": []},

    # bottoms
    {"en": "jeans", "kr": ["청바지", "데님"], "part": "lower", "yolo_classes": []},
    {"en": "slacks", "kr": ["슬랙스"], "part": "lower", "yolo_classes": []},
    {"en": "shorts", "kr": ["반바지"], "part": "lower", "yolo_classes": []},
    {"en": "skirt", "kr": ["치마", "스커트"], "part": "lower", "yolo_classes": []},

    # dress
    {"en": "dress", "kr": ["원피스"], "part": "torso", "yolo_classes": []},

    # outerwear
    {"en": "long coat", "kr": ["롱코트", "코트"], "part": "torso", "yolo_classes": []},
    {"en": "short coat", "kr": ["숏코트"], "part": "torso", "yolo_classes": []},
    {"en": "trench coat", "kr": ["트렌치코트", "트렌치"], "part": "torso", "yolo_classes": []},
    {"en": "puffer jacket", "kr": ["패딩", "푸퍼"], "part": "torso", "yolo_classes": []},
    {"en": "blazer", "kr": ["블레이저", "자켓"], "part": "upper", "yolo_classes": []},

    # bags
    {"en": "backpack", "kr": ["백팩", "배낭"], "part": "hands", "yolo_classes": ["backpack"]},
    {"en": "handbag", "kr": ["핸드백", "숄더백", "토트백"], "part": "hands", "yolo_classes": ["handbag"]},
    {"en": "crossbody bag", "kr": ["크로스백"], "part": "hands", "yolo_classes": []},

    # accessories
    {"en": "hat", "kr": ["모자", "캡"], "part": "head", "yolo_classes": []},
    {"en": "sunglasses", "kr": ["선글라스"], "part": "head", "yolo_classes": []},
    {"en": "tie", "kr": ["넥타이"], "part": "upper", "yolo_classes": ["tie"]},
    {"en": "umbrella", "kr": ["우산"], "part": "hands", "yolo_classes": ["umbrella"]},
    {"en": "watch", "kr": ["시계"], "part": "hands", "yolo_classes": []},
]

def taxonomy_prompts() -> List[str]:
    # slightly richer prompt helps reduce confusion (slippers vs heels)
    return [f"a photo of {x['en']}" for x in ITEM_TAXONOMY]

def taxonomy_best(user_crop: Image.Image) -> Tuple[Dict[str, Any], float]:
    prompts = taxonomy_prompts()
    scores = clip_scores_fast(user_crop, prompts)

    idx = int(torch.tensor(scores).argmax())
    best_item = ITEM_TAXONOMY[idx]
    best_prob = float(scores[idx])
    return best_item, best_prob

# ================= SEARCH: NAVER + KAKAO =================
async def naver_search_once(query: str, display: int = 80, start: int = 1) -> List[Dict[str, Any]]:
    url = "https://openapi.naver.com/v1/search/image"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": int(display),
        "start": int(start),
        "sort": "sim",
        "filter": "large",
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
        ) as c:
            r = await c.get(url, headers=headers, params=params)
            print("[NAVER]", r.status_code, "|", query)
            if r.status_code != 200:
                print("[NAVER ERR]", r.text[:300])
                return []
            data = r.json()
            items = data.get("items", []) or []
            # normalize fields
            out = []
            for it in items:
                out.append({
                    "link": it.get("link"),
                    "thumbnail": it.get("thumbnail"),
                    "originallink": it.get("originallink") or it.get("link"),
                    "title": (it.get("title") or "").replace("<b>", "").replace("</b>", ""),
                    "_source": "naver",
                })
            return out
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
        print("[NAVER TIMEOUT/CONNECT ERROR]", type(e).__name__, "|", query)
        return []

async def kakao_search_once(query: str, size: int = 80, page: int = 1) -> List[Dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        return []
    url = "https://dapi.kakao.com/v2/search/image"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "query": query,
        "sort": "accuracy",
        "page": int(page),
        "size": int(min(max(size, 1), 80)),
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers=headers, params=params)
        print("[KAKAO]", r.status_code, "|", query)
        if r.status_code != 200:
            print("[KAKAO ERR]", r.text[:300])
            return []
        data = r.json()
        docs = data.get("documents", []) or []
        out: List[Dict[str, Any]] = []
        for d in docs:
            out.append({
                "link": d.get("image_url"),
                "thumbnail": d.get("thumbnail_url"),
                "originallink": d.get("doc_url") or d.get("image_url"),
                "title": d.get("display_sitename") or "kakao",
                "_source": "kakao",
                "_w": d.get("width"),
                "_h": d.get("height"),
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

async def search_multi_sources(queries: List[str]) -> List[Dict[str, Any]]:
    tasks = []
    for q in queries:
        if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
            tasks.append(naver_search_once(q, display=NAVER_DISPLAY_EACH, start=1))
        if KAKAO_REST_API_KEY:
            tasks.append(kakao_search_once(q, size=KAKAO_SIZE_EACH, page=1))

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_items: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        all_items.extend(r)

    all_items = merge_dedupe(all_items)
    return all_items[:RAW_POOL_LIMIT]


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

# ================= PROMPTS (better separation) =================
def outfit_gate_prompts() -> List[str]:
    return [
        "a full body street fashion outfit photo",
        "a full body outfit street snap photo",
        "a product photo of an item",
        "a close-up product shot",
        "a screenshot of a shopping webpage with lots of text",
        "a collage of product images",
        "a news photo with text overlay",
        "an illustration or drawing",
    ]

def choose_distractors(item_en: str, item_part: str) -> List[str]:
    if item_en in ("slippers", "sandals", "heels", "sneakers", "boots", "loafers", "dress shoes"):
        return ["slippers", "sandals", "heels", "sneakers", "boots", "loafers", "dress shoes"]
    if "bag" in item_en or item_en in ("backpack", "handbag", "crossbody bag"):
        return ["handbag", "backpack", "tote bag", "crossbody bag", "suitcase"]
    if item_part == "upper":
        return ["t-shirt", "shirt", "hoodie", "knit sweater", "jacket", "coat"]
    if item_part == "lower":
        return ["jeans", "slacks", "shorts", "skirt"]
    if item_part == "head":
        return ["hat", "cap", "sunglasses"]
    return ["clothing", "fashion item", "outfit", "product photo"]

def item_presence_prompts(item_en: str, user_color: str, distractors: List[str]) -> List[str]:
    col = (user_color or "").strip()
    col_phrase = f"{col} " if col else ""

    targets = [
        f"a full body street fashion photo of a person wearing {col_phrase}{item_en}",
        f"a person wearing {col_phrase}{item_en} in an outfit photo",
        f"street style outfit with {col_phrase}{item_en}",
    ]
    bads = [
        f"a product photo of {col_phrase}{item_en}",
        f"a close-up product shot of {col_phrase}{item_en}",
        "a screenshot of a shopping webpage",
    ]
    dist = []
    for d in [x for x in distractors if x != item_en][:4]:
        dist.append(f"a full body street fashion photo of a person wearing {d}")

    return targets + bads + dist

# ================= MAIN =================
@app.post("/recommend/image")
async def recommend_image(
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    requestId: str = Form(...),
    textQuery: str = Form(""),
):
    print("\n[REQ] HIT /recommend/image")
    print("[REQ] requestId=", requestId, "textQuery=", textQuery, "limit=", limit)
    print("[REQ] filename=", image.filename, "content_type=", image.content_type)

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return {"error": "NAVER_CLIENT_ID/SECRET 없음"}
    if not REMBG_OK:
        return {"error": "rembg 미설치/로드 실패 (pip install rembg onnxruntime 필요)"}

    user_img = pil_rgb(await image.read())
    user_q = (textQuery or "").strip()

    drop_counts = defaultdict(int)
    drop_lock = asyncio.Lock()

    async def drop(reason: str):
        async with drop_lock:
            drop_counts[reason] += 1

    # 0) user_mode
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

    # 2) user item crop
    if user_person_crop is not None:
        user_item_crop = crop_region_by_part(user_person_crop, item_part)
    else:
        user_item_crop = center_square_crop(user_img, 0.85)

    user_color, user_color_conf = dominant_color_label_rembg_lab(user_item_crop)
    user_item_features = get_img_features(user_item_crop)

    # 3) Korean-first queries
    color_kor = COLOR_KOR.get(user_color, "")
    item_kor = item_kr_list[0] if item_kr_list else "패션"

    q1 = f"{color_kor} {item_kor} 전신 착샷 코디 룩북 무신사 스냅 OOTD 착용 {user_q}".strip()
    q2 = f"{color_kor} {item_kor} 데일리룩 스트릿 스냅 전신 코디 착용 {user_q}".strip()
    q3 = f"{item_kor} 전신 코디 착샷 룩북 무신사 스냅 착용 {user_q}".strip()
    q4 = f"{item_kor} 코디 전신 OOTD 스트릿룩 착용 {user_q}".strip()
    queries = [q1, q2, q3, q4]

    candidates = await search_multi_sources(queries)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:

        async def process(it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with sem:
                try:
                    url = it.get("link")
                    if not url:
                        await drop("no_url")
                        return None

                    r = await client.get(url)
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

                    # fullbody bbox
                    ok_bbox, bbox = bbox_fullbody_and_feet(img)
                    if not ok_bbox:
                        await drop("bbox_fullbody_fail")
                        return None

                    # pose (soft)
                    ok_pose, pose_meta = pose_fullbody_gate(img)
                    if POSE_GATE_STRICT and (not ok_pose):
                        await drop("pose_fullbody_fail")
                        return None

                    # outfit vs bad
                    gs = clip_scores_fast(img, outfit_gate_prompts())
                    outfit_score = float(gs[0])
                    bad_score = float(max(gs[2:]))  # exclude 2nd outfit-like
                    if not (outfit_score > bad_score + OUTFIT_BAD_MARGIN or outfit_score >= OUTFIT_ABS_MIN):
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

                    # item crop(s)
                    crops = multi_crops_for_part(person_crop, item_part)

                    distractors = choose_distractors(item_en, item_part)
                    prompts = item_presence_prompts(item_en, user_color, distractors)

                    best_local = -1e9
                    best_margin12 = -1e9
                    best_margin_vs_bad = -1e9
                    best_crop = None
                    best_rs: Optional[List[float]] = None
                    best_t_best_real = 0.0

                    for c in crops:
                        # fast color prefilter
                        if COLOR_STRICT_DEFAULT and not fast_color_distance_ok(user_color, c):
                            continue

                        rs = clip_scores_fast(c, prompts)
                        t_best = float(max(rs[0:3]))
                        b_best = float(max(rs[3:6]))
                        margin_vs_bad = float(t_best - b_best)
                        srt = sorted(rs, reverse=True)
                        margin12 = float(srt[0] - srt[1]) if len(srt) >= 2 else 0.0

                        local = 0.70 * t_best + 0.30 * margin_vs_bad
                        if local > best_local:
                            best_local = local
                            best_margin12 = margin12
                            best_margin_vs_bad = margin_vs_bad
                            best_crop = c
                            best_rs = rs
                            best_t_best_real = t_best

                    if best_crop is None or best_rs is None:
                        await drop("item_crop_fail")
                        return None

                    # apply thresholds
                    if best_t_best_real < ITEM_REGION_MIN_PROB:
                        await drop("item_region_low")
                        return None
                    if best_margin12 < ITEM_REGION_MARGIN_MIN:
                        await drop("item_region_ambiguous")
                        return None
                    if best_margin_vs_bad < ITEM_VS_PRODUCT_MIN_MARGIN:
                        await drop("item_vs_product_ambiguous")
                        return None

                    # color strict on best crop
                    cand_color, cand_color_conf = dominant_color_label_fast_lab(best_crop)
                    strict_allowed = (user_color_conf >= COLOR_STRICT_IF_CONF_GE) and (cand_color_conf >= COLOR_STRICT_IF_CONF_GE)
                    strict_ok = (cand_color == user_color) if user_color else True
                    compat_ok = color_compatible(user_color, cand_color) if user_color else True

                    if COLOR_STRICT_DEFAULT and strict_allowed and not strict_ok:
                        await drop("color_strict_mismatch")
                        return None
                    if (not strict_allowed) and COLOR_FALLBACK_COMPAT and (not (strict_ok or compat_ok)):
                        await drop("color_compat_mismatch")
                        return None

                    # CLIP color confirmation
                    if user_color and strict_allowed:
                        c_prompts = color_confirm_prompts(item_en, user_color)
                        if c_prompts:
                            cs = clip_scores_fast(best_crop, c_prompts)
                            color_yes = float(max(cs[0:2]))
                            color_no = float(max(cs[2:])) if len(cs) > 2 else 0.0
                            if color_yes < color_no + 0.02:
                                await drop("clip_color_mismatch")
                                return None

                    # similarity
                    cand_item_features = get_img_features(best_crop)
                    visual_sim = float((user_item_features @ cand_item_features.T).item())

                    # portrait score
                    ar = img.height / max(1, img.width)
                    ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.90

                    # style score
                    style_score = 0.0
                    if user_q:
                        style_prompts = [
                            f"a full body {user_q} outfit photo",
                            f"a {user_q} street fashion lookbook",
                            f"a fashion style of {user_q}",
                        ]
                        style_scores = clip_scores_fast(person_crop, style_prompts)
                        style_score = float(max(style_scores))

                    score = (
                        0.46 * visual_sim +
                        0.28 * best_t_best_real +
                        0.10 * best_margin_vs_bad +
                        0.06 * style_score +
                        0.05 * ar_score +
                        0.05 * float(bbox.get("person_h", 0.0))
                    )
                    if not ok_pose:
                        score -= POSE_GATE_PENALTY

                    title = (it.get("title") or "")
                    landing = it.get("originallink") or url
                    thumb = it.get("thumbnail") or url

                    return {
                        "imageUrl": url,
                        "landingUrl": landing,
                        "thumbUrl": thumb,
                        "title": title,
                        "source": it.get("_source", "unknown"),
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
                            "strict_color_allowed": int(strict_allowed),
                            "strict_ok": int(bool(strict_ok)),
                            "compat_ok": int(bool(compat_ok)),
                            "t_best": round(best_t_best_real, 4),
                            "margin_vs_bad": round(float(best_margin_vs_bad), 4),
                            "margin_12": round(float(best_margin12), 4),
                            "visual_sim": round(visual_sim, 4),
                            "bbox": bbox,
                            "pose": pose_meta,
                            "gate_scores": {"outfit": round(outfit_score, 4), "bad": round(bad_score, 4)},
                        },
                    }

                except Exception:
                    await drop("process_exception")
                    return None

        processed = await asyncio.gather(*[process(it) for it in candidates])

    items = [x for x in processed if x]
    items.sort(key=lambda x: x["score"], reverse=True)
    final = items[: int(limit)]

    for idx, it in enumerate(final, start=1):
        it["rank"] = idx

    return {
        "requestId": requestId,
        "items": final or [],
        "debug": {
            "detected": {
                "user_mode": user_mode,
                "item_en": item_en,
                "item_kr": item_kor,
                "item_prob": round(best_prob, 4),
                "user_color": user_color,
                "user_color_conf": round(float(user_color_conf), 4),
                "queries": queries,
                "sources": {
                    "naver": bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET),
                    "kakao": bool(KAKAO_REST_API_KEY),
                },
                "part": item_part,
                "pose_gate_strict": POSE_GATE_STRICT,
                "outfit_bad_margin": OUTFIT_BAD_MARGIN,
                "outfit_abs_min": OUTFIT_ABS_MIN,
                "item_region_min_prob": ITEM_REGION_MIN_PROB,
                "item_region_margin_min": ITEM_REGION_MARGIN_MIN,
                "item_vs_product_min_margin": ITEM_VS_PRODUCT_MIN_MARGIN,
                "color_strict_default": COLOR_STRICT_DEFAULT,
                "color_strict_if_conf_ge": COLOR_STRICT_IF_CONF_GE,
            },
            "rawCount": len(candidates),
            "passCount": len(items),
            "finalCount": len(final),
            "drop_counts": dict(sorted(drop_counts.items(), key=lambda kv: kv[1], reverse=True)),
        },
    }

# 실행:
# python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug
# pip install rembg onnxruntime
# cd C:\project-outfit-service\outfit-py
# C:\Users\user\anaconda3\envs\class1\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
