from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import io
import os
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import httpx
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, Field
from transformers import CLIPModel, CLIPProcessor
from ultralytics import YOLO

from logic.followup_chat import handle_followup_chat, FollowupReq, FollowupResp



# =========================
# ENV / CONFIG
# =========================
MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
YOLO_DET_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
YOLO_POSE_MODEL_NAME = os.getenv("YOLO_POSE_MODEL_NAME", "yolov8n-pose.pt")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("[BOOT] device =", DEVICE)

MAX_RETURN = int(os.getenv("MAX_RETURN", "8"))
FINAL_LIMIT_DEFAULT = int(os.getenv("FINAL_LIMIT_DEFAULT", "8"))

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "14.0"))
DEFAULT_HEADERS = {
    "User-Agent": os.getenv("HTTP_USER_AGENT", "Mozilla/5.0"),
    "Referer": os.getenv("HTTP_REFERER", "https://search.naver.com/"),
    "Accept": "*/*",
}

CANDIDATE_TIMEOUT_SEC = float(os.getenv("CANDIDATE_TIMEOUT_SEC", "9.0"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "10"))
RAW_POOL_LIMIT = int(os.getenv("RAW_POOL_LIMIT", "260"))
MAX_DOWNLOAD_IMAGES = int(os.getenv("MAX_DOWNLOAD_IMAGES", "180"))

CLIP_MAX_SIDE = int(os.getenv("CLIP_MAX_SIDE", "640"))
MIN_SHORT_SIDE = int(os.getenv("MIN_SHORT_SIDE", "420"))  # target after rescue upscale
MIN_DECODE_SHORT_SIDE_HARD = int(os.getenv("MIN_DECODE_SHORT_SIDE_HARD", "120"))  # true hard-fail below this

NAVER_DISPLAY_EACH = int(os.getenv("NAVER_DISPLAY_EACH", "80"))
KAKAO_SIZE_EACH = int(os.getenv("KAKAO_SIZE_EACH", "80"))

ALLOW_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

SEARCH_SOURCES = [
    s.strip().lower()
    for s in os.getenv("SEARCH_SOURCES", "naver,kakao").split(",")
    if s.strip()
]

# Penalties (user spec)
P_NO_PERSON = float(os.getenv("P_NO_PERSON", "0.25"))
P_OUTFIT_PRODUCT_FAIL = float(os.getenv("P_OUTFIT_PRODUCT_FAIL", "0.20"))
P_ITEM_PRESENCE_FAIL = float(os.getenv("P_ITEM_PRESENCE_FAIL", "0.25"))
P_COLOR_MISMATCH_MIN = float(os.getenv("P_COLOR_MISMATCH_MIN", "0.10"))
P_COLOR_MISMATCH_MAX = float(os.getenv("P_COLOR_MISMATCH_MAX", "0.20"))
P_SIM_LOW = float(os.getenv("P_SIM_LOW", "0.20"))
P_GENDER_UNCERTAIN = float(os.getenv("P_GENDER_UNCERTAIN", "0.08"))

# thresholds to form passed vs salvaged
PASSED_PENALTY_MAX = float(os.getenv("PASSED_PENALTY_MAX", "0.38"))  # <= -> tier A
SALVAGED_PENALTY_MAX = float(os.getenv("SALVAGED_PENALTY_MAX", "1.50"))  # <= -> tier B

# similarity / gates (soft)
SIM_MIN_SOFT = float(os.getenv("SIM_MIN_SOFT", "0.235"))

# =========================
# APP
# =========================
app = FastAPI(title="Styling Recommend API (Always Return 8)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    print("\n=== UNHANDLED ERROR ===")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": repr(exc)})


# =========================
# MODELS: CLIP + YOLO
# =========================
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

yolo_det = YOLO(YOLO_DET_MODEL_NAME)

YOLO_POSE_OK = True
try:
    yolo_pose = YOLO(YOLO_POSE_MODEL_NAME)
except Exception:
    YOLO_POSE_OK = False
    yolo_pose = None


# =========================
# UTILS
# =========================
def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))

def looks_like_image_contenttype(ct: str) -> bool:
    ct = (ct or "").lower()
    return ct.startswith("image/")

def short_side(img: Image.Image) -> int:
    return min(img.size[0], img.size[1])

def _safe_open_image(b: bytes) -> Optional[Image.Image]:
    try:
        return Image.open(io.BytesIO(b)).convert("RGB")
    except Exception:
        return None

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

def upscale_min_short_side(img: Image.Image, target_short: int) -> Image.Image:
    w, h = img.size
    ss = min(w, h)
    if ss >= target_short:
        return img
    scale = target_short / float(max(1, ss))
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    return img.resize((nw, nh), Image.BICUBIC)

@torch.inference_mode()
def _to_tensor(x):
    if torch.is_tensor(x):
        return x
    if hasattr(x, "pooler_output") and torch.is_tensor(x.pooler_output):
        return x.pooler_output
    if hasattr(x, "image_embeds") and torch.is_tensor(x.image_embeds):
        return x.image_embeds
    if hasattr(x, "text_embeds") and torch.is_tensor(x.text_embeds):
        return x.text_embeds
    if hasattr(x, "last_hidden_state") and torch.is_tensor(x.last_hidden_state):
        return x.last_hidden_state[:, 0, :]
    if isinstance(x, dict):
        for k in ("pooler_output", "image_embeds", "text_embeds", "last_hidden_state"):
            if k in x and torch.is_tensor(x[k]):
                t = x[k]
                if k == "last_hidden_state":
                    t = t[:, 0, :]
                return t
    raise RuntimeError(f"Unexpected feature output type: {type(x)}")

TEXT_FEAT_CACHE: Dict[Tuple[str, ...], torch.Tensor] = {}

def _texts_key(texts: List[str]) -> Tuple[str, ...]:
    return tuple([t.strip() for t in texts])

@torch.inference_mode()
def clip_text_features(texts: List[str]) -> torch.Tensor:
    key = _texts_key(texts)
    feat = TEXT_FEAT_CACHE.get(key)
    if feat is not None:
        return feat
    t_in = clip_processor(text=list(texts), return_tensors="pt", padding=True, truncation=True)
    t_in = {k: v.to(DEVICE) for k, v in t_in.items()}
    out = clip_model.get_text_features(
        input_ids=t_in["input_ids"],
        attention_mask=t_in.get("attention_mask"),
    )
    txt_feat = _to_tensor(out)
    txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
    TEXT_FEAT_CACHE[key] = txt_feat.detach().float().cpu()
    return TEXT_FEAT_CACHE[key]

@torch.inference_mode()
def clip_image_features(img: Image.Image) -> torch.Tensor:
    img = resize_max_side(img, CLIP_MAX_SIDE)
    i_in = clip_processor(images=img, return_tensors="pt")
    i_in = {k: v.to(DEVICE) for k, v in i_in.items()}
    out = clip_model.get_image_features(**i_in)
    img_feat = _to_tensor(out)
    if img_feat.ndim == 1:
        img_feat = img_feat.unsqueeze(0)
    img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
    return img_feat

@torch.inference_mode()
def clip_score_image_text(img: Image.Image, texts: List[str]) -> np.ndarray:
    img_feat = clip_image_features(img)  # [1, d]
    txt_feat = clip_text_features(texts).to(DEVICE)  # [n, d]
    sims = (img_feat @ txt_feat.T).squeeze(0).detach().float().cpu().numpy()
    return sims

@torch.inference_mode()
def clip_scores_fast(img: Image.Image, prompts: List[str]) -> List[float]:
    sims = clip_score_image_text(img, prompts)
    x = sims - float(np.max(sims))
    ex = np.exp(x)
    p = ex / (np.sum(ex) + 1e-12)
    return p.astype(np.float32).tolist()

@torch.inference_mode()
def clip_image_embed(img: Image.Image) -> np.ndarray:
    feats = clip_image_features(img)  # [1, d], normalized
    emb = feats[0].detach().float().cpu().numpy()
    emb = emb / (np.linalg.norm(emb) + 1e-12)
    return emb

def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# =========================
# COLOR
# =========================
COLOR_ALIASES = {
    "black": "black", "검정": "black", "검은": "black", "검은색": "black", "블랙": "black",
    "white": "white", "흰": "white", "흰색": "white", "화이트": "white",
    "beige": "beige", "베이지": "beige", "아이보리": "beige", "크림": "beige", "ivory": "beige", "cream": "beige",
    "brown": "brown", "브라운": "brown", "갈색": "brown", "초코": "brown",
    "navy": "navy", "네이비": "navy", "곤색": "navy",
    "blue": "blue", "블루": "blue", "파랑": "blue", "파란": "blue", "청색": "blue",
    "gray": "gray", "grey": "gray", "그레이": "gray", "회색": "gray", "차콜": "gray", "charcoal": "gray",
    "green": "green", "그린": "green", "초록": "green", "녹색": "green",
    "red": "red", "레드": "red", "빨강": "red", "적색": "red", "버건디": "red", "burgundy": "red",
}

KOREAN_COLOR_KEYWORDS = {
    "black": "검정 블랙",
    "white": "흰색 화이트",
    "beige": "베이지 아이보리 크림",
    "brown": "브라운 갈색",
    "navy": "네이비 곤색",
    "blue": "블루 파랑",
    "gray": "그레이 회색 차콜",
    "green": "그린 초록",
    "red": "레드 빨강 버건디",
}

COLOR_RGB = {
    "black": np.array([20, 20, 20], dtype=np.float32),
    "white": np.array([235, 235, 235], dtype=np.float32),
    "beige": np.array([210, 190, 160], dtype=np.float32),
    "brown": np.array([120, 80, 50], dtype=np.float32),
    "navy": np.array([25, 35, 70], dtype=np.float32),
    "blue": np.array([60, 110, 200], dtype=np.float32),
    "gray": np.array([140, 140, 140], dtype=np.float32),
    "green": np.array([60, 140, 80], dtype=np.float32),
    "red": np.array([180, 60, 60], dtype=np.float32),
}

def normalize_color(color_raw: str) -> Optional[str]:
    s = (color_raw or "").strip().lower()
    if not s:
        return None
    s = s.replace("색", "").strip()
    if s in COLOR_ALIASES:
        return COLOR_ALIASES[s]
    for tok in s.replace("/", " ").replace(",", " ").split():
        if tok in COLOR_ALIASES:
            return COLOR_ALIASES[tok]
    return None

def dominant_rgb(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.resize((96, 96), Image.BILINEAR), dtype=np.float32)
    flat = arr.reshape(-1, 3)
    lum = flat.mean(axis=1)
    mask = (lum > 18) & (lum < 240)
    if np.any(mask):
        flat = flat[mask]
    if flat.shape[0] == 0:
        return arr.reshape(-1, 3).mean(axis=0)
    return np.median(flat, axis=0)

def infer_color_from_item_img(item_img: Image.Image) -> Tuple[Optional[str], Dict[str, Any]]:
    rgb = dominant_rgb(center_square_crop(item_img, 0.85))
    best = None
    best_dist = 1e9
    for name, proto in COLOR_RGB.items():
        dist = float(np.linalg.norm(rgb - proto))
        if dist < best_dist:
            best_dist = dist
            best = name
    if best is None or best_dist > 160.0:
        return None, {"infer": "fail", "dominantRGB": [float(x) for x in rgb], "bestDist": float(best_dist)}
    return best, {"infer": "ok", "dominantRGB": [float(x) for x in rgb], "best": best, "bestDist": float(best_dist)}

def region_color_label_conf(region: Image.Image) -> Tuple[str, float]:
    rgb = dominant_rgb(center_square_crop(region, 0.78))
    best, best_dist = "black", 1e9
    for name, proto in COLOR_RGB.items():
        dist = float(np.linalg.norm(rgb - proto))
        if dist < best_dist:
            best_dist = dist
            best = name
    conf = float(clamp(1.0 - best_dist / 160.0, 0.0, 1.0))
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

def color_penalty(user_color: Optional[str], region: Image.Image) -> Tuple[float, Dict[str, Any]]:
    if not user_color:
        return 0.0, {"color": "skip"}
    cand, conf = region_color_label_conf(region)
    if cand == user_color:
        return 0.0, {"user": user_color, "cand": cand, "conf": round(float(conf), 4), "match": 1, "compat": 1, "p": 0.0}
    compat = int(color_compatible(user_color, cand))
    if compat:
        p = P_COLOR_MISMATCH_MIN
    else:
        p = P_COLOR_MISMATCH_MAX
    return float(p), {"user": user_color, "cand": cand, "conf": round(float(conf), 4), "match": 0, "compat": compat, "p": float(p)}


# =========================
# YOLO
# =========================
def detect_person_boxes(img: Image.Image, conf: float = 0.25) -> List[Tuple[float, float, float, float, float]]:
    w, h = img.size
    r = yolo_det.predict(img, verbose=False, conf=conf)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return []
    boxes = r.boxes.xyxy.cpu().numpy()
    cls = r.boxes.cls.cpu().numpy().astype(int)
    confs = r.boxes.conf.cpu().numpy() if hasattr(r.boxes, "conf") else np.ones((len(cls),), dtype=np.float32)

    out = []
    for (x1, y1, x2, y2), c, cf in zip(boxes, cls, confs):
        if int(c) != 0:
            continue
        x1n, y1n, x2n, y2n = float(x1 / w), float(y1 / h), float(x2 / w), float(y2 / h)
        out.append((x1n, y1n, x2n, y2n, float(cf)))
    out.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    return out

def crop_by_norm(img: Image.Image, x1n: float, y1n: float, x2n: float, y2n: float) -> Image.Image:
    w, h = img.size
    x1 = int(max(0, min(w - 1, x1n * w)))
    x2 = int(max(1, min(w, x2n * w)))
    y1 = int(max(0, min(h - 1, y1n * h)))
    y2 = int(max(1, min(h, y2n * h)))
    if x2 <= x1 + 2 or y2 <= y1 + 2:
        return img
    return img.crop((x1, y1, x2, y2))


# =========================
# CATEGORY / TAXONOMY
# =========================
def map_gender(gender_raw: str) -> str:
    g = (gender_raw or "").strip().lower()
    if g in ("man", "male", "m", "남", "남성"):
        return "male"
    if g in ("woman", "female", "f", "여", "여성"):
        return "female"
    return "unknown"

def map_category(cat_raw: str) -> str:
    c = (cat_raw or "").strip().lower()
    mapping = {
        "top": "top",
        "bottom": "bottom",
        "pants": "bottom",
        "jeans": "bottom",
        "skirt": "skirt",
        "dress": "dress",
        "outer": "outerwear",
        "outerwear": "outerwear",
        "coat": "outerwear",
        "jacket": "outerwear",
        "shoes": "footwear",
        "shoe": "footwear",
        "footwear": "footwear",
        "bag": "bag",
    }
    return mapping.get(c, c or "unknown")

CATEGORY_KW = {
    "top": "상의 셔츠 티셔츠 니트 후드",
    "bottom": "하의 바지 청바지 슬랙스 팬츠",
    "skirt": "치마 스커트",
    "dress": "원피스 드레스",
    "outerwear": "아우터 코트 자켓 트렌치",
    "footwear": "신발 착용샷",
    "bag": "가방 착용샷 크로스백 숄더백 토트백",
    "unknown": "",
}

def build_search_query(
    text_query: str,
    category_mapped: str,
    gender_mapped: str,
    normalized_color: Optional[str],
) -> str:
    parts: List[str] = []
    if text_query:
        parts.append(text_query.strip())
    else:
        parts.append(CATEGORY_KW.get(category_mapped, ""))

    if normalized_color:
        parts.append(KOREAN_COLOR_KEYWORDS.get(normalized_color, ""))
        parts.append(normalized_color)

    if gender_mapped == "male":
        parts.append("남자 남성 남자코디 남친룩 남자패션")
    elif gender_mapped == "female":
        parts.append("여자 여성 여자코디 여친룩 여성룩")

    parts.append(CATEGORY_KW.get(category_mapped, ""))
    parts.append("전신 착샷 코디 룩북 스트릿 스냅 데일리룩 무신사 스냅 코디북 OOTD 착용샷")
    return " ".join(dict.fromkeys(" ".join(parts).split()))

ITEM_TAXONOMY: List[Dict[str, Any]] = [
    {"en": "sneakers", "kr": ["운동화", "스니커즈"], "part": "feet"},
    {"en": "boots", "kr": ["부츠"], "part": "feet"},
    {"en": "loafers", "kr": ["로퍼"], "part": "feet"},
    {"en": "dress shoes", "kr": ["구두", "드레스슈즈"], "part": "feet"},

    {"en": "t-shirt", "kr": ["티셔츠", "반팔"], "part": "upper"},
    {"en": "shirt", "kr": ["셔츠"], "part": "upper"},
    {"en": "hoodie", "kr": ["후드", "후드티"], "part": "upper"},
    {"en": "knit sweater", "kr": ["니트", "스웨터"], "part": "upper"},

    {"en": "jeans", "kr": ["청바지", "데님"], "part": "lower"},
    {"en": "slacks", "kr": ["슬랙스"], "part": "lower"},
    {"en": "shorts", "kr": ["반바지"], "part": "lower"},
    {"en": "skirt", "kr": ["치마", "스커트"], "part": "lower"},

    {"en": "dress", "kr": ["원피스"], "part": "torso"},

    {"en": "long coat", "kr": ["롱코트", "코트"], "part": "torso"},
    {"en": "trench coat", "kr": ["트렌치코트", "트렌치"], "part": "torso"},
    {"en": "puffer jacket", "kr": ["패딩", "푸퍼"], "part": "torso"},
    {"en": "blazer", "kr": ["블레이저", "자켓"], "part": "upper"},

    {"en": "backpack", "kr": ["백팩", "배낭"], "part": "hands"},
    {"en": "handbag", "kr": ["핸드백", "숄더백", "토트백"], "part": "hands"},
    {"en": "crossbody bag", "kr": ["크로스백"], "part": "hands"},

    {"en": "hat", "kr": ["모자", "캡"], "part": "head"},
    {"en": "sunglasses", "kr": ["선글라스"], "part": "head"},
    {"en": "tie", "kr": ["넥타이"], "part": "upper"},
    {"en": "umbrella", "kr": ["우산"], "part": "hands"},
    {"en": "watch", "kr": ["시계"], "part": "hands"},
]

def taxonomy_prompts() -> List[str]:
    return [f"a photo of {x['en']}" for x in ITEM_TAXONOMY]

def crop_region_by_part(person_crop: Image.Image, part: str) -> Image.Image:
    w, h = person_crop.size
    part = part or "torso"
    if part == "head":
        return safe_crop(person_crop, 0, h * 0.00, w, h * 0.25)
    if part == "upper":
        return safe_crop(person_crop, 0, h * 0.10, w, h * 0.58)
    if part == "lower":
        return safe_crop(person_crop, 0, h * 0.42, w, h * 0.98)
    if part == "feet":
        return safe_crop(person_crop, 0, h * 0.64, w, h * 1.00)
    if part == "hands":
        return safe_crop(person_crop, 0, h * 0.22, w, h * 0.90)
    return safe_crop(person_crop, 0, h * 0.10, w, h * 0.90)

def multi_crops_for_part(person_crop: Image.Image, part: str) -> List[Image.Image]:
    w, h = person_crop.size
    crops: List[Image.Image] = []
    crops.append(crop_region_by_part(person_crop, part))

    if part == "feet":
        crops.append(safe_crop(person_crop, 0, h * 0.58, w, h * 1.00))
        crops.append(safe_crop(person_crop, w * 0.06, h * 0.60, w * 0.94, h * 1.00))
    elif part == "hands":
        crops.append(safe_crop(person_crop, 0, h * 0.16, w, h * 0.96))
        crops.append(safe_crop(person_crop, w * 0.04, h * 0.14, w * 0.96, h * 0.94))
    elif part == "upper":
        crops.append(safe_crop(person_crop, 0, h * 0.04, w, h * 0.70))
        crops.append(safe_crop(person_crop, w * 0.05, h * 0.06, w * 0.95, h * 0.66))
    elif part == "lower":
        crops.append(safe_crop(person_crop, 0, h * 0.30, w, h * 1.00))
        crops.append(safe_crop(person_crop, w * 0.05, h * 0.36, w * 0.95, h * 0.99))
    else:
        crops.append(safe_crop(person_crop, 0, h * 0.04, w, h * 0.96))

    crops.append(center_square_crop(person_crop, 0.72))
    out = [c for c in crops if short_side(c) >= 120]
    return out

def taxonomy_best(user_crop: Image.Image) -> Tuple[Dict[str, Any], float]:
    prompts = taxonomy_prompts()
    probs = clip_scores_fast(user_crop, prompts)
    idx = int(np.argmax(np.array(probs, dtype=np.float32)))
    best_item = ITEM_TAXONOMY[idx]
    best_prob = float(probs[idx])
    return best_item, best_prob


# =========================
# PROMPTS / SOFT GATES
# =========================
OUTFIT_POS_PROMPTS = [
    "a street style outfit photo",
    "a person wearing an outfit",
    "a lookbook outfit photo",
    "a mirror selfie outfit photo",
    "a full body outfit photo",
    "a full-length street style photo",
]

NEG_PRODUCT_PROMPTS_COMMON = [
    "a product photo on white background",
    "a studio product photo",
    "a catalog product image",
    "a flat lay product photo",
    "an isolated product photo",
    "a mannequin product photo",
    "a screenshot of an online shopping page",
]

GENDER_MALE_PROMPTS = [
    "a full body photo of a man wearing an outfit",
    "men street style full body",
]
GENDER_FEMALE_PROMPTS = [
    "a full body photo of a woman wearing an outfit",
    "women street style full body",
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
        "a collage of product images",
    ]
    dist = []
    for d in [x for x in distractors if x != item_en][:4]:
        dist.append(f"a full body street fashion photo of a person wearing {d}")
    return targets + bads + dist


# =========================
# SEARCH SOURCES (Naver + Kakao)
# =========================
async def naver_search_once(query: str, display: int = 80, start: int = 1) -> List[Dict[str, Any]]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    url = "https://openapi.naver.com/v1/search/image"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": int(display), "start": int(start), "sort": "sim", "filter": "large"}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        ) as c:
            r = await c.get(url, headers=headers, params=params)
            print("[NAVER]", r.status_code, "|", query)
            if r.status_code != 200:
                return []
            data = r.json()
            items = data.get("items", []) or []
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
    except Exception:
        return []

async def kakao_search_once(query: str, size: int = 80, page: int = 1) -> List[Dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        return []
    url = "https://dapi.kakao.com/v2/search/image"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query, "sort": "accuracy", "page": int(page), "size": int(min(max(size, 1), 80))}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=DEFAULT_HEADERS) as c:
            r = await c.get(url, headers=headers, params=params)
            print("[KAKAO]", r.status_code, "|", query)
            if r.status_code != 200:
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
    except Exception:
        return []

def merge_dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for c in items:
        key = (c.get("link") or "")[:400] or (c.get("originallink") or "")[:400]
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out

async def search_multi_sources(queries: List[str]) -> List[Dict[str, Any]]:
    tasks = []
    for q in queries:
        if "naver" in SEARCH_SOURCES and NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
            tasks.append(naver_search_once(q, display=NAVER_DISPLAY_EACH, start=1))
        if "kakao" in SEARCH_SOURCES and KAKAO_REST_API_KEY:
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


# =========================
# HARD FAIL MINIMIZED: only download/decode + tiny-after-rescue
# =========================
async def _fetch_image_bytes(url: str, client: httpx.AsyncClient) -> Optional[bytes]:
    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        ct = r.headers.get("content-type", "")
        if not looks_like_image_contenttype(ct):
            return None
        return r.content
    except Exception:
        return None


# =========================
# SCORER
# =========================
@dataclass
class ScoredCand:
    it: Dict[str, Any]
    url: str
    ok_download: bool
    penalty: float
    base_rank: float
    sim_region: float
    sim_global: float
    tier: str
    debug: Dict[str, Any] = field(default_factory=dict)

def _tier_from_penalty(p: float) -> str:
    if p <= PASSED_PENALTY_MAX:
        return "A"
    if p <= SALVAGED_PENALTY_MAX:
        return "B"
    return "B"

async def score_candidates(
    cands: List[Dict[str, Any]],
    *,
    category: str,
    gender: str,
    normalized_color: Optional[str],
    user_item_embed: np.ndarray,
    user_q: str,
    item_en: str,
    item_part: str,
    client: httpx.AsyncClient,
    concurrency: int = 10,
) -> Tuple[List[ScoredCand], Dict[str, int]]:
    sem = asyncio.Semaphore(concurrency)
    drop_counts = defaultdict(int)
    lock = asyncio.Lock()

    async def bump(k: str):
        async with lock:
            drop_counts[k] += 1

    async def process_one(it: Dict[str, Any]) -> Optional[ScoredCand]:
        try:
            async with asyncio.timeout(CANDIDATE_TIMEOUT_SEC):
                url = it.get("link") or ""
                if not url:
                    await bump("no_url")
                    return None

                async with sem:
                    b = await _fetch_image_bytes(url, client)
                if not b:
                    await bump("download_fail")
                    return None  # HARD FAIL
                img = _safe_open_image(b)
                if img is None:
                    await bump("decode_fail")
                    return None  # HARD FAIL

                ss0 = short_side(img)
                if ss0 < MIN_DECODE_SHORT_SIDE_HARD:
                    await bump("too_small_hard")
                    return None  # HARD FAIL (truly tiny)
                if ss0 < MIN_SHORT_SIDE:
                    img = upscale_min_short_side(img, MIN_SHORT_SIDE)
                    await bump("too_small_rescued")

                # person crop or fallback center crop
                persons = detect_person_boxes(img)
                used_person = False
                if persons:
                    x1n, y1n, x2n, y2n, pconf = persons[0]
                    person_crop = crop_by_norm(img, x1n, y1n, x2n, y2n)
                    used_person = True
                else:
                    person_crop = center_square_crop(img, 0.90)
                    pconf = 0.0
                    await bump("no_person")
                penalty = 0.0
                reasons: Dict[str, Any] = {}

                if not used_person:
                    penalty += P_NO_PERSON
                    reasons["no_person"] = float(P_NO_PERSON)
                    reasons["person_fallback"] = "center_crop"

                # outfit/product soft gate
                pos_outfit = float(np.max(clip_score_image_text(img, OUTFIT_POS_PROMPTS)))
                neg_prod = float(np.max(clip_score_image_text(img, NEG_PRODUCT_PROMPTS_COMMON)))
                outfit_ok = (pos_outfit > (neg_prod - 0.02))  # lenient
                if not outfit_ok:
                    penalty += P_OUTFIT_PRODUCT_FAIL
                    reasons["outfit_product_fail"] = float(P_OUTFIT_PRODUCT_FAIL)

                # item presence (best crop over multiple)
                crops = multi_crops_for_part(person_crop, item_part)
                if not crops:
                    crops = [center_square_crop(person_crop, 0.78)]
                    await bump("no_item_crops_rescued")

                distractors = choose_distractors(item_en, item_part)
                prompts = item_presence_prompts(item_en, normalized_color or "", distractors)

                best_crop = None
                best_t = -1.0
                best_bad = -1.0
                best_margin = -1.0
                best_prob = -1.0
                for c in crops:
                    rs = clip_scores_fast(c, prompts)
                    t_best = float(max(rs[0:3]))
                    b_best = float(max(rs[3:7]))
                    margin = float(t_best - b_best)
                    prob = float(t_best)
                    if margin + prob > best_margin + best_prob:
                        best_margin = margin
                        best_prob = prob
                        best_t = t_best
                        best_bad = b_best
                        best_crop = c

                if best_crop is None:
                    best_crop = center_square_crop(person_crop, 0.78)
                    best_t = 0.0
                    best_bad = 0.0
                    best_margin = 0.0

                item_ok = (best_t >= 0.12) and (best_margin >= 0.00)
                if not item_ok:
                    penalty += P_ITEM_PRESENCE_FAIL
                    reasons["item_presence_fail"] = float(P_ITEM_PRESENCE_FAIL)
                    reasons["item_presence"] = {"t": round(best_t, 4), "bad": round(best_bad, 4), "m": round(best_margin, 4)}

                # color mismatch penalty
                cpen, cdbg = color_penalty(normalized_color, best_crop)
                if cpen > 0:
                    penalty += float(cpen)
                    reasons["color_mismatch"] = float(cpen)
                reasons["color_dbg"] = cdbg

                # similarity (region)
                cand_region_embed = clip_image_embed(best_crop)
                sim_region = cos_sim(user_item_embed, cand_region_embed)

                if sim_region < SIM_MIN_SOFT:
                    penalty += P_SIM_LOW
                    reasons["sim_low"] = float(P_SIM_LOW)
                    reasons["sim_region"] = round(float(sim_region), 4)

                # gender uncertain penalty (soft)
                male_s = float(np.max(clip_score_image_text(img, GENDER_MALE_PROMPTS)))
                female_s = float(np.max(clip_score_image_text(img, GENDER_FEMALE_PROMPTS)))
                gender_conf = abs(male_s - female_s)
                if gender in ("male", "female"):
                    if gender_conf < 0.03:
                        penalty += P_GENDER_UNCERTAIN
                        reasons["gender_uncertain"] = float(P_GENDER_UNCERTAIN)
                reasons["gender_scores"] = {"male": round(male_s, 4), "female": round(female_s, 4), "conf": round(float(gender_conf), 4)}

                # style bonus (text query)
                style_score = 0.0
                if user_q:
                    style_prompts = [
                        f"a full body {user_q} outfit photo",
                        f"a {user_q} street fashion lookbook",
                        f"a fashion style of {user_q}",
                    ]
                    style_score = float(max(clip_scores_fast(person_crop, style_prompts)))

                # portrait bonus
                ar = img.height / max(1, img.width)
                ar_score = ar if ar >= 1.0 else 0.90

                # global embed (for last-resort topN)
                global_crop = person_crop if used_person else center_square_crop(img, 0.90)
                cand_global_embed = clip_image_embed(global_crop)
                sim_global = cos_sim(user_item_embed, cand_global_embed)

                # base_rank = similarity + signals - penalty
                base_rank = (
                    1.70 * sim_region +
                    0.22 * pos_outfit +
                    0.06 * style_score +
                    0.04 * ar_score -
                    0.10 * neg_prod -
                    1.00 * penalty
                )

                tier = _tier_from_penalty(penalty)
                dbg = {
                    "url": url,
                    "source": it.get("_source", "unknown"),
                    "title": (it.get("title") or ""),
                    "penalty": round(float(penalty), 4),
                    "penaltyReasons": reasons,
                    "scores": {
                        "simRegion": round(float(sim_region), 4),
                        "simGlobal": round(float(sim_global), 4),
                        "posOutfit": round(float(pos_outfit), 4),
                        "negProduct": round(float(neg_prod), 4),
                        "styleScore": round(float(style_score), 4),
                        "arScore": round(float(ar_score), 4),
                        "baseRank": round(float(base_rank), 4),
                    },
                    "yolo": {"personCount": len(persons), "personConf": round(float(pconf), 4)},
                }

                return ScoredCand(
                    it=it,
                    url=url,
                    ok_download=True,
                    penalty=float(penalty),
                    base_rank=float(base_rank),
                    sim_region=float(sim_region),
                    sim_global=float(sim_global),
                    tier=tier,
                    debug=dbg,
                )
        except asyncio.TimeoutError:
            await bump("candidate_timeout")
            return None
        except Exception:
            await bump("process_exception")
            return None

    results = await asyncio.gather(*(process_one(c) for c in cands), return_exceptions=False)
    ok = [r for r in results if r is not None]
    return ok, dict(sorted(drop_counts.items(), key=lambda kv: kv[1], reverse=True))


# =========================
# API: RECOMMEND (ALWAYS RETURN 8 IF ANY DOWNLOAD OK)
# =========================
@app.post("/api/v1/recommend/image")
async def recommend_image(
    requestId: str = Form(""),
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    textQuery: str = Form(""),
    category: str = Form(""),
    gender: str = Form(""),
    userColor: str = Form(""),
    guestId: str = Form(""),      
    nickname: str = Form(""),     
    style: str = Form(""),        

):
    print("[GUEST]", guestId, nickname, style)
    t0 = time.time()
    warnings: List[str] = []

    request_id = requestId.strip() if (requestId and requestId.strip()) else f"ui-{int(time.time()*1000)}"
    category_mapped = map_category(category)
    gender_mapped = map_gender(gender)

    file_bytes = await image.read()
    user_img = _safe_open_image(file_bytes)
    if user_img is None:
        return JSONResponse({"error": "Invalid image upload (decode failed)."}, status_code=400)

    persons_u = detect_person_boxes(user_img)
    if persons_u:
        x1n, y1n, x2n, y2n, _ = persons_u[0]
        user_person_crop = crop_by_norm(user_img, x1n, y1n, x2n, y2n)
        user_base_for_clip = user_person_crop
        user_mode = "person_wearing"
    else:
        user_person_crop = None
        user_base_for_clip = center_square_crop(user_img, 0.85)
        user_mode = "item_only"

    best_item, best_prob = taxonomy_best(user_base_for_clip)
    item_en = best_item["en"]
    item_kr_list = best_item["kr"]
    item_part = best_item["part"]

    if user_person_crop is not None:
        user_item_crop = crop_region_by_part(user_person_crop, item_part)
    else:
        user_item_crop = center_square_crop(user_img, 0.85)

    user_item_embed = clip_image_embed(user_item_crop)

    normalized_color = normalize_color(userColor)
    color_infer_dbg: Dict[str, Any] = {}
    if not normalized_color:
        inferred, dbg = infer_color_from_item_img(user_item_crop)
        color_infer_dbg = dbg
        normalized_color = inferred
        if normalized_color:
            warnings.append(f"Color inferred: {normalized_color}")
        else:
            warnings.append("Color not recognized/inferred -> color penalty skipped.")
    else:
        warnings.append(f"Color normalized: {userColor} -> {normalized_color}")
    
    style_norm = (style or "").strip().lower()
    STYLE_KW = {
        "minimal": "미니멀",
        "casual": "캐주얼 데일리",
        "street": "스트릿 스냅",
        "classic": "클래식 포멀",
    }
    style_kor = STYLE_KW.get(style_norm, "")

    # textQuery 보강: 사용자가 말을 안 해도 스타일이 검색어에 반영됨
    textQuery_eff = " ".join([x for x in [style_kor, textQuery] if x]).strip()


    search_query = build_search_query(textQuery_eff, category_mapped, gender_mapped, normalized_color)

    item_kor = item_kr_list[0] if item_kr_list else "패션"
    color_kor = KOREAN_COLOR_KEYWORDS.get(normalized_color, "") if normalized_color else ""
    q1 = f"{color_kor} {item_kor} 전신 착샷 코디 룩북 무신사 스냅 OOTD 착용 {textQuery_eff}".strip()
    q2 = f"{color_kor} {item_kor} 데일리룩 스트릿 스냅 전신 코디 착용 {textQuery_eff}".strip()
    q3 = f"{item_kor} 전신 코디 착샷 룩북 무신사 스냅 착용 {textQuery_eff}".strip()
    q4 = f"{item_kor} 코디 전신 OOTD 스트릿룩 착용 {textQuery_eff}".strip()
    queries = [q1, q2, q3, q4]

    candidates = await search_multi_sources(queries)
    candidates = candidates[:MAX_DOWNLOAD_IMAGES]

    raw_count = {
        "raw": len(candidates),
        "sources": {
            "naver": bool("naver" in SEARCH_SOURCES and NAVER_CLIENT_ID and NAVER_CLIENT_SECRET),
            "kakao": bool("kakao" in SEARCH_SOURCES and KAKAO_REST_API_KEY),
        },
    }

    final_n = min(int(limit or MAX_RETURN), MAX_RETURN)
    if final_n <= 0:
        final_n = MAX_RETURN

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        scored, drop_counts = await score_candidates(
            candidates,
            category=category_mapped,
            gender=gender_mapped,
            normalized_color=normalized_color,
            user_item_embed=user_item_embed,
            user_q=textQuery_eff or "",
            item_en=item_en,
            item_part=item_part,
            client=client,
            concurrency=MAX_CONCURRENCY,
        )

    # If no downloadable candidates -> return 0 (only case)
    if not scored:
        latency = time.time() - t0
        return JSONResponse({
            "requestId": request_id,
            "query": search_query,
            "category": category_mapped if category_mapped else category,
            "gender": gender_mapped if gender_mapped else gender,
            "userColor": userColor,
            "normalizedColor": normalized_color,
            "gateUsed": "none_downloaded",
            "rawCount": raw_count,
            "rawCandidateCount": len(candidates),
            "passCount": 0,
            "finalCount": 0,
            "items": [],
            "debug": {
                "detected": {
                    "user_mode": user_mode,
                    "item_en": item_en,
                    "item_kr": item_kor,
                    "item_prob": round(best_prob, 4),
                    "item_part": item_part,
                    "queries": queries,
                    "clip_text_cache_size": len(TEXT_FEAT_CACHE),
                    "color_infer_debug": color_infer_dbg,
                },
                "drop_counts": drop_counts,
            },
            "warnings": warnings + ["No downloadable candidates."],
            "device": DEVICE,
            "latencySec": round(float(latency), 2),
            "guest": {
                "guestId": guestId,
                "nickname": nickname,
                "style": style,
            },
        })

    # Build passed + salvaged
    passed = [s for s in scored if s.penalty <= PASSED_PENALTY_MAX]
    salvaged = [s for s in scored if s.penalty > PASSED_PENALTY_MAX]

    passed.sort(key=lambda x: x.base_rank, reverse=True)
    salvaged.sort(key=lambda x: x.base_rank, reverse=True)

    selected: List[ScoredCand] = []
    used_urls = set()

    def take_from(lst: List[ScoredCand], need: int):
        nonlocal selected, used_urls
        for s in lst:
            if len(selected) >= need:
                break
            if s.url in used_urls:
                continue
            selected.append(s)
            used_urls.add(s.url)

    take_from(passed, final_n)

    if len(selected) < final_n:
        take_from(salvaged, final_n)

    # Last resort: CLIP similarity top-N among all downloaded (tier C)
    if len(selected) < final_n:
        remaining = [s for s in scored if s.url not in used_urls]
        remaining.sort(key=lambda x: x.sim_global, reverse=True)
        for s in remaining:
            if len(selected) >= final_n:
                break
            s.tier = "C"
            selected.append(s)
            used_urls.add(s.url)

    # If still not enough (rare): allow duplicates to force 8
    if len(selected) < final_n:
        scored_sorted = sorted(scored, key=lambda x: x.sim_global, reverse=True)
        i = 0
        while len(selected) < final_n and scored_sorted:
            s = scored_sorted[i % len(scored_sorted)]
            s2 = ScoredCand(
                it=s.it,
                url=s.url,
                ok_download=s.ok_download,
                penalty=s.penalty,
                base_rank=s.base_rank,
                sim_region=s.sim_region,
                sim_global=s.sim_global,
                tier="C",
                debug=dict(s.debug),
            )
            s2.debug["forced_duplicate"] = 1
            selected.append(s2)
            i += 1

    # finalize
    items_out = []
    for i, s in enumerate(selected[:final_n], start=1):
        it = s.it
        url = it.get("link") or ""
        landing = it.get("originallink") or url
        thumb = it.get("thumbnail") or url
        items_out.append({
            "rank": i,
            "tier": s.tier,
            "rankScore": float(s.base_rank),
            "penalty": float(s.penalty),
            "imageUrl": url,
            "thumbUrl": thumb,
            "landingUrl": landing,
            "title": (it.get("title") or ""),
            "source": it.get("_source", "unknown"),
            "debug": s.debug,
        })

    latency = time.time() - t0
    gate_used = "A_then_B_then_C"
    return JSONResponse({
        "requestId": request_id,
        "query": search_query,
        "category": category_mapped if category_mapped else category,
        "gender": gender_mapped if gender_mapped else gender,
        "userColor": userColor,
        "normalizedColor": normalized_color,
        "gateUsed": gate_used,
        "rawCount": raw_count,
        "rawCandidateCount": len(candidates),
        "downloadedCount": len(scored),
        "passedCount": len(passed),
        "salvagedCount": len(salvaged),
        "finalCount": len(items_out),
        "items": items_out,
        "debug": {
            "detected": {
                "user_mode": user_mode,
                "item_en": item_en,
                "item_kr": item_kor,
                "item_prob": round(best_prob, 4),
                "item_part": item_part,
                "queries": queries,
                "penaltyThresholdA": PASSED_PENALTY_MAX,
                "penaltyThresholdB": SALVAGED_PENALTY_MAX,
                "sim_min_soft": SIM_MIN_SOFT,
                "candidate_timeout_sec": CANDIDATE_TIMEOUT_SEC,
                "clip_text_cache_size": len(TEXT_FEAT_CACHE),
                "color_infer_debug": color_infer_dbg,
                "penalties": {
                    "no_person": P_NO_PERSON,
                    "outfit_product_fail": P_OUTFIT_PRODUCT_FAIL,
                    "item_presence_fail": P_ITEM_PRESENCE_FAIL,
                    "color_mismatch_min": P_COLOR_MISMATCH_MIN,
                    "color_mismatch_max": P_COLOR_MISMATCH_MAX,
                    "sim_low": P_SIM_LOW,
                    "gender_uncertain": P_GENDER_UNCERTAIN,
                },
            },
            "drop_counts": drop_counts,
        },
        "warnings": warnings,
        "device": DEVICE,
        "latencySec": round(float(latency), 2),
        "guest": {
            "guestId": guestId,
            "nickname": nickname,
            "style": style,
        },
    })


@app.post("/recommend/image")
async def recommend_image_alias(
    requestId: str = Form(""),
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    textQuery: str = Form(""),
    category: str = Form(""),
    gender: str = Form(""),
    userColor: str = Form(""),
    guestId: str = Form(""),   
    nickname: str = Form(""),  
    style: str = Form(""),     
):
    return await recommend_image(
        requestId=requestId,
        image=image,
        limit=limit,
        textQuery=textQuery,
        category=category,
        gender=gender,
        userColor=userColor,
        guestId=guestId,      
        nickname=nickname,    
        style=style,          
    )


# =========================
# API: LLM CHAT (OpenAI Responses API)
# =========================

@app.post("/api/v1/chat", response_model=FollowupResp)
async def chat_followup(req: FollowupReq):
    print(f"[CHAT] guestId={req.guestId} nickname={req.nickname!r} style={req.style!r} text={req.text!r}")
    return await handle_followup_chat(req)


# python -m uvicorn main:app --reload
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug
