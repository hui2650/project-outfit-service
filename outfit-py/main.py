from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

"""
Outfit Recommendation API (FastAPI) — single-file main.py
YOLOv8 Person Gate + Image2Image Similarity (ALL categories) + Color Gate + (Full/3-4 body by category) + Gender + LLM Chat

Goal:
✅ MUST be outfit photo (person wearing outfit)  -> YOLO person gate
✅ Prefer "most similar item" -> rank mainly by image-to-image similarity on region crop
✅ Correct color (KR/EN accepted), if userColor empty -> infer from uploaded item image
✅ Body requirement by category:
   - footwear: requires feet visible (full/near-full)
   - bag: allows 3/4 body even in strict
   - outerwear/top/bottom/skirt/dress: allows 3/4 body even in strict (no hard feet requirement)
✅ Block product/shop images strongly:
   - STRICT: domain blacklist + strong NEG prompts
   - LOOSE : NO domain blacklist (keep candidates), still uses NEG prompts by category

Stability goals (to stop "pending forever"):
✅ Per-candidate hard timeout so a single bad image can't hang the whole request
✅ Text-embedding cache for CLIP prompt lists (big speed-up on CPU)
✅ Defensive exception handling inside gate

Endpoint:
POST /api/v1/recommend/image
multipart/form-data: image, limit, textQuery, category, gender, userColor

Chat:
POST /chat
"""

import asyncio
import io
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from transformers import CLIPModel, CLIPProcessor

# YOLO (ultralytics)
# pip install ultralytics
from ultralytics import YOLO


# =========================
# ENV / CONFIG
# =========================

MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
YOLO_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")  # small & fast

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MAX_CANDIDATES_PER_SOURCE = int(os.getenv("MAX_CANDIDATES_PER_SOURCE", "80"))
MAX_DOWNLOAD_IMAGES = int(os.getenv("MAX_DOWNLOAD_IMAGES", "180"))
MAX_RETURN = int(os.getenv("MAX_RETURN", "8"))

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "14.0"))
DEFAULT_HEADERS = {
    "User-Agent": os.getenv("HTTP_USER_AGENT", "Mozilla/5.0"),
    "Referer": os.getenv("HTTP_REFERER", "https://search.naver.com/"),
    "Accept": "*/*",
}

# Safety: per-candidate processing time limit (prevents infinite pending)
CANDIDATE_TIMEOUT_SEC = float(os.getenv("CANDIDATE_TIMEOUT_SEC", "6.0"))

ALLOW_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

SEARCH_SOURCES = [
    s.strip().lower()
    for s in os.getenv("SEARCH_SOURCES", "naver,kakao,openverse").split(",")
    if s.strip()
]

# OpenAI (LLM Chat)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


# =========================
# HARD BLOCK: shop/product domains
# IMPORTANT:
# - STRICT: block domains early
# - LOOSE : do NOT domain-block (otherwise candidates die before similarity)
# =========================

BLOCK_URL_SUBSTRINGS = [
    "shop-phinf.pstatic.net",
    "shop1.phinf.naver.net",
    "smartstore",
    "search.shopping",
    "storefarm",
    "/product/",
    "shopping",
    "product",
]

def is_blocked_url(url: str) -> bool:
    u = (url or "").lower()
    return any(s in u for s in BLOCK_URL_SUBSTRINGS)


# =========================
# GATE THRESHOLDS
# =========================

STRICT = {
    "MIN_SHORT_SIDE": 520,
    "OUTFIT_MIN": 0.26,
    "OUTFIT_MARGIN": 0.10,   # pos - neg
    "SIM_MIN": 0.305,
    "GENDER_MARGIN": 0.04,
    "COLOR_MAX_DIST_FOOT": 90.0,
    "COLOR_MAX_DIST_OTHER": 105.0,

    # Person gate (YOLO)
    "MAX_PERSON": 1,
    "PERSON_HEIGHT_MIN": 0.58,   # bbox_h / img_h
    "HEAD_TOP_MAX": 0.20,        # bbox_y1 / img_h
    "FEET_BOTTOM_MIN": 0.90,
    "CANDIDATE_TIMEOUT_SEC": 8.0,     # only enforced for footwear by category rule
}

LOOSE = {
    "MIN_SHORT_SIDE": 380,
    "OUTFIT_MIN": 0.22,
    "OUTFIT_MARGIN": 0.06,
    "SIM_MIN": 0.265,
    "GENDER_MARGIN": 0.02,
    "COLOR_MAX_DIST_FOOT": 115.0,
    "COLOR_MAX_DIST_OTHER": 135.0,

    # Person gate (YOLO)
    "MAX_PERSON": 2,
    "PERSON_HEIGHT_MIN": 0.46,   # allow 3/4
    "HEAD_TOP_MAX": 0.28,
    "FEET_BOTTOM_MIN": 0.80,
    "CANDIDATE_TIMEOUT_SEC": 8.0,     # only enforced for footwear by category rule
}

CATEGORY_PERSON_OVERRIDE = {
    "bag": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.44, "HEAD_TOP_MAX": 0.30, "FEET_BOTTOM_MIN": 0.72, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.38, "HEAD_TOP_MAX": 0.35, "FEET_BOTTOM_MIN": 0.62, "MAX_PERSON": 3},
    },
    "footwear": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.55, "HEAD_TOP_MAX": 0.25, "FEET_BOTTOM_MIN": 0.88, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.42, "HEAD_TOP_MAX": 0.35, "FEET_BOTTOM_MIN": 0.78, "MAX_PERSON": 3},
    },
    "outerwear": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.44, "HEAD_TOP_MAX": 0.30, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.38, "HEAD_TOP_MAX": 0.36, "MAX_PERSON": 3},
    },
    "top": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.42, "HEAD_TOP_MAX": 0.32, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.36, "HEAD_TOP_MAX": 0.38, "MAX_PERSON": 3},
    },
    "bottom": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.48, "HEAD_TOP_MAX": 0.30, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.40, "HEAD_TOP_MAX": 0.36, "MAX_PERSON": 3},
    },
    "skirt": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.48, "HEAD_TOP_MAX": 0.30, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.40, "HEAD_TOP_MAX": 0.36, "MAX_PERSON": 3},
    },
    "dress": {
        "STRICT": {"PERSON_HEIGHT_MIN": 0.46, "HEAD_TOP_MAX": 0.30, "MAX_PERSON": 2},
        "LOOSE":  {"PERSON_HEIGHT_MIN": 0.38, "HEAD_TOP_MAX": 0.36, "MAX_PERSON": 3},
    },
}


# =========================
# APP
# =========================

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELS: CLIP + YOLO
# =========================

clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# ---- CLIP text feature cache (big speed-up) ----
# Cache on CPU to save VRAM; moved to DEVICE only when used in matmul (via .to).
TEXT_FEAT_CACHE: Dict[Tuple[str, ...], torch.Tensor] = {}

def _texts_key(texts: List[str]) -> Tuple[str, ...]:
    return tuple([t.strip() for t in texts])

@torch.inference_mode()
def clip_text_features(texts: List[str]) -> torch.Tensor:
    """Return normalized text features on CPU, cached by exact prompt list."""
    key = _texts_key(texts)
    feat = TEXT_FEAT_CACHE.get(key)
    if feat is not None:
        return feat
    t_in = clip_processor(text=list(texts), return_tensors="pt", padding=True)
    t_in = {k: v.to(DEVICE) for k, v in t_in.items()}
    txt_out = clip_model.get_text_features(
        input_ids=t_in["input_ids"],
        attention_mask=t_in.get("attention_mask"),
    )
    txt_feat = _to_tensor(txt_out)
    txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
    TEXT_FEAT_CACHE[key] = txt_feat.detach().float().cpu()
    return TEXT_FEAT_CACHE[key]

@torch.inference_mode()
def clip_image_features(img: Image.Image) -> torch.Tensor:
    """Return normalized image feature on DEVICE."""
    i_in = clip_processor(images=img, return_tensors="pt")
    i_in = {k: v.to(DEVICE) for k, v in i_in.items()}
    img_out = clip_model.get_image_features(**i_in)
    img_feat = _to_tensor(img_out)
    if img_feat.ndim == 1:
        img_feat = img_feat.unsqueeze(0)
    img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
    return img_feat


@torch.inference_mode()
def clip_score_from_imgfeat(img_feat: torch.Tensor, texts: List[str]) -> np.ndarray:
    """Similarity using a precomputed image feature."""
    txt_feat = clip_text_features(texts).to(DEVICE)
    sims = (img_feat @ txt_feat.T).squeeze(0).detach().float().cpu().numpy()
    return sims



yolo_model = YOLO(YOLO_MODEL_NAME)


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
    if isinstance(x, dict):
        t = x.get("pooler_output") or x.get("image_embeds") or x.get("text_embeds")
        if torch.is_tensor(t):
            return t
    raise RuntimeError(f"Unexpected feature output type: {type(x)}")


@torch.inference_mode()
def _clip_text_features(texts: List[str]) -> torch.Tensor:
    """Return normalized text features [n, d] on DEVICE."""
    inputs = clip_processor(text=texts, return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    out = clip_model.get_text_features(
        input_ids=inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
    )
    feats = _to_tensor(out)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


@torch.inference_mode()
def _clip_image_features(img: Image.Image) -> torch.Tensor:
    """Return normalized image features [1, d] on DEVICE."""
    inputs = clip_processor(images=img, return_tensors="pt")
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    out = clip_model.get_image_features(**inputs)
    feats = _to_tensor(out)
    if feats.ndim == 1:
        feats = feats.unsqueeze(0)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


# =========================
# HELPERS
# =========================

def _safe_open_image(b: bytes) -> Optional[Image.Image]:
    try:
        return Image.open(io.BytesIO(b)).convert("RGB")
    except Exception:
        return None

def _short_side(img: Image.Image) -> int:
    return min(img.size[0], img.size[1])

def dedup_candidates(cands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for c in cands:
        key = (c.get("imageUrlDirect") or c.get("imageUrl") or "")[:400]
        if not key:
            key = (c.get("landingUrl") or "")[:400]
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out

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


# =========================
# COLOR NORMALIZATION + INFER (KR + EN)
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


# Hard cap per color for RGB-distance (prevents 'beige' matching gray/blue backgrounds)
# We still use proto_rgb_from_region(), so these caps can be relatively tight.
COLOR_DIST_CAP_OTHER = {
    "beige": 110.0,
    "white": 95.0,
    "black": 90.0,
    "gray": 105.0,
    "brown": 95.0,
    "navy": 90.0,
    "blue": 95.0,
    "green": 95.0,
    "red": 95.0,
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
    rgb = dominant_rgb(item_img)
    best = None
    best_dist = 1e9
    for name, proto in COLOR_RGB.items():
        dist = float(np.linalg.norm(rgb - proto))
        if dist < best_dist:
            best_dist = dist
            best = name
    if best is None or best_dist > 140.0:
        return None, {"infer": "fail", "dominantRGB": [float(x) for x in rgb], "bestDist": best_dist}
    return best, {"infer": "ok", "dominantRGB": [float(x) for x in rgb], "best": best, "bestDist": best_dist}

# ✅ NEW: robust "prototype-matched" region color (better than median when background dominates)
def proto_rgb_from_region(region: Image.Image, proto: np.ndarray, keep_ratio: float = 0.15) -> Tuple[np.ndarray, float]:
    arr = np.asarray(region.resize((128, 128), Image.BILINEAR), dtype=np.float32).reshape(-1, 3)

    # drop too dark/too bright pixels (pure black/white background)
    lum = arr.mean(axis=1)
    arr2 = arr[(lum > 18) & (lum < 240)]
    if arr2.shape[0] >= 50:
        arr = arr2

    d = np.linalg.norm(arr - proto[None, :], axis=1)
    k = max(30, int(len(d) * keep_ratio))
    # take k closest-to-proto pixels -> average becomes "item-like color"
    idx = np.argpartition(d, k)[:k]
    rgb = arr[idx].mean(axis=0)
    dist = float(np.linalg.norm(rgb - proto))
    return rgb, dist


# =========================
# CLIP PROMPTS
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
]

NEG_PRODUCT_PROMPTS_STRONG = NEG_PRODUCT_PROMPTS_COMMON + [
    "a close-up photo of the item only",
    "a close-up product photo",
    "a screenshot of an online shopping page",
    "a product detail cutout image",
]

def neg_prompts_for_category(category: str) -> List[str]:
    if category in ("footwear", "bag"):
        return NEG_PRODUCT_PROMPTS_STRONG
    return NEG_PRODUCT_PROMPTS_COMMON

GENDER_MALE_PROMPTS = [
    "a full body photo of a man wearing an outfit",
    "men street style full body",
]
GENDER_FEMALE_PROMPTS = [
    "a full body photo of a woman wearing an outfit",
    "women street style full body",
]

# ✅ Cache text features once (huge speed-up)
_TEXT_FEAT_CACHE: Dict[Tuple[str, ...], torch.Tensor] = {}
def _get_text_feats_cached(texts: List[str]) -> torch.Tensor:
    key = tuple(texts)
    t = _TEXT_FEAT_CACHE.get(key)
    if t is None:
        t = _clip_text_features(texts)
        _TEXT_FEAT_CACHE[key] = t
    return t

@torch.inference_mode()
def clip_score_image_text(img: Image.Image, texts: List[str]) -> np.ndarray:
    """CLIP similarity between one image and many texts. Uses cached text features."""
    img_feat = clip_image_features(img)  # [1, d] on DEVICE
    txt_feat = clip_text_features(texts).to(DEVICE)  # [n, d] on DEVICE
    sims = (img_feat @ txt_feat.T).squeeze(0).detach().float().cpu().numpy()
    return sims

@torch.inference_mode()
def clip_image_embed(img: Image.Image) -> np.ndarray:
    feats = _clip_image_features(img)  # [1, d] normalized
    emb = feats[0].detach().float().cpu().numpy()
    emb = emb / (np.linalg.norm(emb) + 1e-12)
    return emb

def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# =========================
# SEARCH QUERY build (bias only)
# =========================

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
    parts.append("전신 착샷 코디 착장 룩북 스트릿 스냅 데일리룩 무신사 스냅 코디북")
    return " ".join(dict.fromkeys(" ".join(parts).split()))


# =========================
# SEARCH SOURCES
# =========================

async def naver_image_search(query: str, limit: int, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("Missing NAVER_CLIENT_ID/NAVER_CLIENT_SECRET")

    url = "https://openapi.naver.com/v1/search/image"
    params = {"query": query, "display": min(limit, 100), "start": 1, "sort": "sim"}
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    r = await client.get(url, params=params, headers=headers)
    r.raise_for_status()
    j = r.json()

    items = []
    for it in j.get("items", []):
        img = it.get("link")
        thumb = it.get("thumbnail") or img
        landing = it.get("link")
        if not img:
            continue
        items.append({"source": "naver", "imageUrl": thumb, "imageUrlDirect": img, "landingUrl": landing or img})
    return items

async def kakao_image_search(query: str, limit: int, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    if not KAKAO_REST_API_KEY:
        raise RuntimeError("Missing KAKAO_REST_API_KEY")

    url = "https://dapi.kakao.com/v2/search/image"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query, "size": min(limit, 80), "sort": "accuracy"}
    r = await client.get(url, params=params, headers=headers)
    r.raise_for_status()
    j = r.json()

    out = []
    for doc in j.get("documents", []):
        img = doc.get("image_url")
        if not img:
            continue
        out.append({"source": "kakao", "imageUrl": img, "imageUrlDirect": img, "landingUrl": doc.get("doc_url") or img})
    return out

async def openverse_image_search(query: str, limit: int, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    return []


# =========================
# YOLO PERSON DETECT
# =========================

def detect_person_boxes(img: Image.Image) -> List[Tuple[float, float, float, float, float]]:
    """
    Returns list of (x1,y1,x2,y2,conf) in normalized coordinates [0..1]
    """
    arr = np.asarray(img)
    res = yolo_model.predict(arr, verbose=False, conf=0.25)
    if not res or len(res) == 0:
        return []

    r0 = res[0]
    if r0.boxes is None:
        return []

    boxes = r0.boxes
    xyxy = boxes.xyxy.cpu().numpy()
    conf = boxes.conf.cpu().numpy()
    cls = boxes.cls.cpu().numpy()

    w, h = img.size
    out = []
    for (x1, y1, x2, y2), c, k in zip(xyxy, conf, cls):
        if int(k) != 0:
            continue
        x1n = float(max(0.0, min(1.0, x1 / w)))
        x2n = float(max(0.0, min(1.0, x2 / w)))
        y1n = float(max(0.0, min(1.0, y1 / h)))
        y2n = float(max(0.0, min(1.0, y2 / h)))
        out.append((x1n, y1n, x2n, y2n, float(c)))

    out.sort(key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
    return out


def apply_cfg_override(category: str, gate_cfg: Dict[str, Any], mode: str) -> Dict[str, Any]:
    cfg = dict(gate_cfg)
    ov = CATEGORY_PERSON_OVERRIDE.get(category, {}).get(mode, {})
    cfg.update(ov)
    return cfg


# =========================
# REGION CROPS using PERSON bbox
# =========================

def crop_by_norm(img: Image.Image, x1n: float, y1n: float, x2n: float, y2n: float) -> Image.Image:
    w, h = img.size
    x1 = int(max(0, min(w-1, x1n * w)))
    x2 = int(max(1, min(w,   x2n * w)))
    y1 = int(max(0, min(h-1, y1n * h)))
    y2 = int(max(1, min(h,   y2n * h)))
    if x2 <= x1 + 2 or y2 <= y1 + 2:
        return img
    return img.crop((x1, y1, x2, y2))

def region_from_person(img: Image.Image, category: str, pb: Tuple[float,float,float,float,float]) -> Image.Image:
    x1, y1, x2, y2, _ = pb
    if category == "footwear":
        yy1 = y1 + 0.65 * (y2 - y1)
        return crop_by_norm(img, x1, yy1, x2, y2)
    if category == "bag":
        yy1 = y1 + 0.18 * (y2 - y1)
        yy2 = y1 + 0.78 * (y2 - y1)
        xx1 = max(0.0, x1 - 0.08)
        xx2 = min(1.0, x2 + 0.08)
        return crop_by_norm(img, xx1, yy1, xx2, yy2)
    if category in ("top", "outerwear"):
        # focus torso (reduce background + face)
        yy1 = y1 + 0.18 * (y2 - y1)
        yy2 = y1 + 0.78 * (y2 - y1)
        xx1 = min(1.0, max(0.0, x1 + 0.05))
        xx2 = min(1.0, max(0.0, x2 - 0.05))
        return crop_by_norm(img, xx1, yy1, xx2, yy2)
    if category in ("bottom", "skirt"):
        yy1 = y1 + 0.38 * (y2 - y1)
        yy2 = y2
        return crop_by_norm(img, x1, yy1, x2, yy2)
    if category == "dress":
        yy1 = y1 + 0.10 * (y2 - y1)
        yy2 = y2
        return crop_by_norm(img, x1, yy1, x2, yy2)
    return crop_by_norm(img, x1, y1, x2, y2)


def pass_color_gate(
    category: str,
    normalized_color: Optional[str],
    region_img: Image.Image,
    gate_cfg: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    if not normalized_color:
        return True, {"colorGate": "skip"}

    proto = COLOR_RGB.get(normalized_color)
    if proto is None:
        return True, {"colorGate": "unknown_color_skip", "normalized": normalized_color}

    # ✅ use proto-matched rgb (more accurate when background exists)
    keep_ratio = 0.12 if category in ("bag", "footwear") else 0.18
    rgb, dist = proto_rgb_from_region(region_img, proto, keep_ratio=keep_ratio)

    thr = float(gate_cfg["COLOR_MAX_DIST_FOOT"]) if category == "footwear" else float(gate_cfg["COLOR_MAX_DIST_OTHER"])
    if category != "footwear":
        thr = min(thr, float(COLOR_DIST_CAP_OTHER.get(normalized_color, thr)))
    ok = dist <= thr

    return ok, {
        "colorGate": "ok" if ok else "fail",
        "normalized": normalized_color,
        "dominantRGB": [float(x) for x in rgb],
        "dist": float(dist),
        "thr": float(thr),
        "region": category,
        "method": "proto_rgb_from_region",
        "keep_ratio": float(keep_ratio),

    }


# =========================
# GATE
# =========================

@dataclass
class GateStats:
    total: int = 0
    blocked_url: int = 0
    downloaded: int = 0
    download_fail: int = 0
    decode_fail: int = 0
    too_small: int = 0
    person_fail: int = 0
    body_fail: int = 0
    outfit_fail: int = 0
    neg_fail: int = 0
    color_fail: int = 0
    sim_fail: int = 0
    gender_fail: int = 0
    ok: int = 0

    def to_str(self) -> str:
        return (
            f"total={self.total} blocked_url={self.blocked_url} downloaded={self.downloaded} "
            f"download_fail={self.download_fail} decode_fail={self.decode_fail} too_small={self.too_small} "
            f"person_fail={self.person_fail} body_fail={self.body_fail} outfit_fail={self.outfit_fail} neg_fail={self.neg_fail} "
            f"color_fail={self.color_fail} sim_fail={self.sim_fail} gender_fail={self.gender_fail} ok={self.ok}"
        )


async def _fetch_image_bytes(url: str, client: httpx.AsyncClient) -> Optional[bytes]:
    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        return r.content
    except Exception:
        return None


def category_requires_feet(category: str) -> bool:
    return category == "footwear"


async def _run_gate(
    cands: List[Dict[str, Any]],
    *,
    category: str,
    gender: str,
    normalized_color: Optional[str],
    item_embed: np.ndarray,
    client: httpx.AsyncClient,
    gate_cfg: Dict[str, Any],
    mode: str,
    concurrency: int = 10,
) -> Tuple[List[Dict[str, Any]], GateStats]:
    stats = GateStats(total=len(cands))
    sem = asyncio.Semaphore(concurrency)

    cfg = apply_cfg_override(category, gate_cfg, mode)
    neg_prompts = neg_prompts_for_category(category)

    do_domain_block = (mode == "STRICT")

    async def process_one(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal stats
        try:
            # ✅ per-candidate hard timeout (prevents infinite pending)
            async with asyncio.timeout(CANDIDATE_TIMEOUT_SEC):
                url = c.get("imageUrlDirect") or c.get("imageUrl") or ""
                if not url:
                    stats.download_fail += 1
                    return None

                if do_domain_block and is_blocked_url(url):
                    stats.blocked_url += 1
                    return None

                async with sem:
                    b = await _fetch_image_bytes(url, client)
                if not b:
                    stats.download_fail += 1
                    return None
                stats.downloaded += 1

                img = _safe_open_image(b)
                if img is None:
                    stats.decode_fail += 1
                    return None

                if _short_side(img) < int(cfg["MIN_SHORT_SIDE"]):
                    stats.too_small += 1
                    return None

                persons = detect_person_boxes(img)
                if len(persons) == 0:
                    stats.person_fail += 1
                    return None

                if len(persons) > int(cfg["MAX_PERSON"]):
                    a0 = (persons[0][2]-persons[0][0]) * (persons[0][3]-persons[0][1])
                    a1 = (persons[1][2]-persons[1][0]) * (persons[1][3]-persons[1][1])
                    if a0 < 1.6 * a1:
                        stats.person_fail += 1
                        return None

                pb = persons[0]
                x1, y1, x2, y2, conf = pb
                ph = (y2 - y1)

                if ph < float(cfg["PERSON_HEIGHT_MIN"]):
                    stats.body_fail += 1
                    return None
                if y1 > float(cfg["HEAD_TOP_MAX"]):
                    stats.body_fail += 1
                    return None
                if category_requires_feet(category):
                    if y2 < float(cfg["FEET_BOTTOM_MIN"]):
                        stats.body_fail += 1
                        return None

                pos = float(np.max(clip_score_image_text(img, OUTFIT_POS_PROMPTS)))
                neg = float(np.max(clip_score_image_text(img, neg_prompts)))

                if pos < float(cfg["OUTFIT_MIN"]):
                    stats.outfit_fail += 1
                    return None

                margin = float(cfg["OUTFIT_MARGIN"])
                if mode == "LOOSE" and category not in ("footwear", "bag"):
                    margin = max(0.02, margin - 0.03)

                if (pos - neg) < margin:
                    stats.neg_fail += 1
                    return None

                region = region_from_person(img, category, pb)

                ok_color, color_dbg = pass_color_gate(category, normalized_color, region, cfg)
                if not ok_color:
                    stats.color_fail += 1
                    return None

                reg_emb = clip_image_embed(region)
                sim_region = cos_sim(item_embed, reg_emb)
                if sim_region < float(cfg["SIM_MIN"]):
                    stats.sim_fail += 1
                    return None

                male_s = female_s = 0.0
                if gender in ("male", "female"):
                    male_s = float(np.max(clip_score_image_text(img, GENDER_MALE_PROMPTS)))
                    female_s = float(np.max(clip_score_image_text(img, GENDER_FEMALE_PROMPTS)))
                    gm = float(cfg["GENDER_MARGIN"])
                    if gender == "male":
                        if (male_s - female_s) < gm:
                            stats.gender_fail += 1
                            return None
                    else:
                        if (female_s - male_s) < gm:
                            stats.gender_fail += 1
                            return None

                gender_bonus = 0.0
                if gender == "male":
                    gender_bonus = max(0.0, male_s - female_s)
                elif gender == "female":
                    gender_bonus = max(0.0, female_s - male_s)

                rank = (1.55 * sim_region) + (0.18 * pos) + (0.06 * gender_bonus) - (0.10 * neg)

                out = dict(c)
                out["rankScore"] = float(rank)
                out["debug"] = {
                    "yolo": {
                        "personCount": len(persons),
                        "personBox": [x1, y1, x2, y2],
                        "personConf": conf,
                        "personHeight": ph,
                        "cfg": {
                            "PERSON_HEIGHT_MIN": cfg.get("PERSON_HEIGHT_MIN"),
                            "HEAD_TOP_MAX": cfg.get("HEAD_TOP_MAX"),
                            "FEET_BOTTOM_MIN": cfg.get("FEET_BOTTOM_MIN"),
                            "MAX_PERSON": cfg.get("MAX_PERSON"),
                            "feetRequired": category_requires_feet(category),
                        },
                    },
                    "posOutfit": pos,
                    "negProduct": neg,
                    "outfit_margin_used": margin,
                    "simRegion": sim_region,
                    "genderMale": male_s,
                    "genderFemale": female_s,
                    "genderBonus": gender_bonus,
                    "minShortSide": _short_side(img),
                    "color": color_dbg,
                    "mode": mode,
                    "negPromptMode": "strong" if category in ("footwear", "bag") else "product_only",
                    "domainBlockApplied": do_domain_block,
                    "candidateTimeoutSec": CANDIDATE_TIMEOUT_SEC,
                }
                stats.ok += 1
                return out
        except Exception:
            # don't let any exception hang/kill whole request
            stats.download_fail += 1
            return None

    results = await asyncio.gather(*(process_one(c) for c in cands), return_exceptions=False)
    ok = [r for r in results if r is not None]
    return ok, stats


# =========================
# API: RECOMMEND
# =========================

@app.post("/api/v1/recommend/image")
async def recommend_image(
    image: UploadFile = File(...),
    limit: int = Form(8),
    textQuery: str = Form(""),
    category: str = Form(""),
    gender: str = Form(""),
    userColor: str = Form(""),
):
    t0 = time.time()
    warnings: List[str] = []

    raw_count = {"naver": 0, "kakao": 0, "openverse": 0, "deduped": 0, "processedOk": 0}
    request_id = f"ui-{int(time.time()*1000)}"

    category_mapped = map_category(category)
    gender_mapped = map_gender(gender)

    file_bytes = await image.read()
    item_img = _safe_open_image(file_bytes)
    if item_img is None:
        return JSONResponse({"error": "Invalid image upload (decode failed)."}, status_code=400)

    item_embed = clip_image_embed(item_img)

    normalized_color = normalize_color(userColor)
    color_infer_dbg: Dict[str, Any] = {}
    if not normalized_color:
        inferred, dbg = infer_color_from_item_img(item_img)
        color_infer_dbg = dbg
        normalized_color = inferred
        if normalized_color:
            warnings.append(f"Color inferred from item image: {normalized_color}")
        else:
            warnings.append("Color not recognized/inferred -> color gate skipped.")
    else:
        warnings.append(f"Color normalized: {userColor} -> {normalized_color}")

    search_query = build_search_query(textQuery, category_mapped, gender_mapped, normalized_color)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        tasks = []
        sources = SEARCH_SOURCES or ["naver", "kakao", "openverse"]

        if "naver" in sources:
            tasks.append(naver_image_search(search_query, MAX_CANDIDATES_PER_SOURCE, client))
        if "kakao" in sources:
            if not KAKAO_REST_API_KEY:
                warnings.append("Kakao REST API key missing -> skipping Kakao search.")
            else:
                tasks.append(kakao_image_search(search_query, MAX_CANDIDATES_PER_SOURCE, client))
        if "openverse" in sources:
            tasks.append(openverse_image_search(search_query, MAX_CANDIDATES_PER_SOURCE, client))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cands: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                warnings.append(f"Search source error: {repr(r)}")
                continue
            if isinstance(r, list):
                cands.extend(r)

        for c in cands:
            s = c.get("source")
            if s in raw_count:
                raw_count[s] += 1

        cands = dedup_candidates(cands)
        raw_count["deduped"] = len(cands)

        cands = cands[:MAX_DOWNLOAD_IMAGES]

        ok_items, stats_strict = await _run_gate(
            cands,
            category=category_mapped,
            gender=gender_mapped,
            normalized_color=normalized_color,
            item_embed=item_embed,
            client=client,
            gate_cfg=STRICT,
            mode="STRICT",
            concurrency=10,
        )
        gate_used = "strict"
        warnings.append(f"GATE_STATS_STRICT: {stats_strict.to_str()}")

        if len(ok_items) == 0:
            gate_used = "loose"
            warnings.append("No results in STRICT -> fallback to LOOSE.")
            ok_items, stats_loose = await _run_gate(
                cands,
                category=category_mapped,
                gender=gender_mapped,
                normalized_color=normalized_color,
                item_embed=item_embed,
                client=client,
                gate_cfg=LOOSE,
                mode="LOOSE",
                concurrency=10,
            )
            warnings.append(f"GATE_STATS_LOOSE: {stats_loose.to_str()}")

    raw_count["processedOk"] = len(ok_items)

    ok_items.sort(key=lambda x: x.get("rankScore", 0.0), reverse=True)
    items = []
    for i, it in enumerate(ok_items[: min(MAX_RETURN, int(limit or MAX_RETURN))], start=1):
        items.append(
            {
                "rank": i,
                "rankScore": it["rankScore"],
                "imageUrl": it.get("imageUrl"),
                "imageUrlDirect": it.get("imageUrlDirect") or it.get("imageUrl"),
                "landingUrl": it.get("landingUrl") or it.get("imageUrlDirect") or it.get("imageUrl"),
                "source": it.get("source"),
                "debug": it.get("debug", {}),
            }
        )

    latency = time.time() - t0
    return JSONResponse(
        {
            "query": search_query,
            "category": category_mapped if category_mapped else category,
            "gender": gender_mapped if gender_mapped else gender,
            "userColor": userColor,
            "normalizedColor": normalized_color,
            "gateUsed": gate_used,
            "rawCount": raw_count,
            "itemsCount": len(items),
            "items": items,
            "sources": SEARCH_SOURCES or ["naver", "kakao", "openverse"],
            "device": DEVICE,
            "warnings": warnings,
            "requestId": request_id,
            "latencySec": round(latency, 2),
            "received": {
                "requestId": request_id,
                "query": textQuery or "",
                "category_raw": category,
                "category_mapped": category_mapped,
                "gender_raw": gender,
                "gender_mapped": gender_mapped,
                "userColor_raw": userColor,
                "normalizedColor": normalized_color,
                "colorInferDebug": color_infer_dbg,
                "form_keys": ["image", "limit", "textQuery", "category", "gender", "userColor"],
                "policy": {
                    "domain_block_strict_only": True,
                    "must_have_person": True,
                    "footwear_requires_feet": True,
                    "bag_allows_three_quarter_body": True,
                    "outerwear_allows_three_quarter_body": True,
                    "neg_prompts_by_category": True,
                    "candidate_timeout_sec": CANDIDATE_TIMEOUT_SEC,
                    "clip_text_cache": True,
                    "color_method": "proto_rgb_from_region",
                },
            },
        }
    )


# =========================
# API: LLM CHAT (OpenAI Responses API)
# =========================

class ChatReq(BaseModel):
    messages: List[Dict[str, str]]
    system: Optional[str] = None

class ChatResp(BaseModel):
    reply: str

async def call_openai_responses(messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")

    input_items: List[Dict[str, str]] = []
    if system:
        input_items.append({"role": "system", "content": system})
    input_items.extend(messages)

    payload = {"model": OPENAI_MODEL, "input": input_items}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    reply = data.get("output_text")
    if isinstance(reply, str) and reply.strip():
        return reply.strip()

    out = data.get("output", [])
    texts: List[str] = []
    if isinstance(out, list):
        for item in out:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                content = item.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "output_text":
                            t = part.get("text", "")
                            if t:
                                texts.append(t)
    return "\n".join(texts).strip()

@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    try:
        reply = await call_openai_responses(req.messages, req.system)
        return ChatResp(reply=reply)
    except Exception as e:
        return ChatResp(reply=f"[chat_error] {repr(e)}")
