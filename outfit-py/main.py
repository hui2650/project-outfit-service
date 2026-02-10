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

from fastapi import Request
import traceback

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

# Kakao optional
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

# ✅ Full-body gates
PORTRAIT_AR_MIN = 1.02

# [TUNED] 전신 기준 조금 강화
BBOX_FEET_Y_MIN = 0.92

# [TUNED] 아이템 확신도 기준 강화
ITEM_TOP1_MIN_PROB = 0.22
ITEM_MARGIN_MIN = 0.08

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

SEARCH_SOURCES = [
    s.strip().lower()
    for s in os.getenv("SEARCH_SOURCES", "naver,kakao,openverse").split(",")
    if s.strip()
]

# OpenAI (LLM Chat)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    print("\n=== UNHANDLED ERROR ===")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": repr(exc)})

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
# ================= MODELS =================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("[BOOT] device =", device)

clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device).eval()
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


    # 2) fallback: vision_model만 사용 (text_model 절대 타지 않음)
    if feats is None or not torch.is_tensor(feats):
        vision_out = clip_model.vision_model(pixel_values=pixel_values)
        pooled = vision_out.pooler_output
        feats = clip_model.visual_projection(pooled)


@torch.inference_mode()
def clip_score_from_imgfeat(img_feat: torch.Tensor, texts: List[str]) -> np.ndarray:
    """Similarity using a precomputed image feature."""
    txt_feat = clip_text_features(texts).to(DEVICE)
    sims = (img_feat @ txt_feat.T).squeeze(0).detach().float().cpu().numpy()
    return sims


yolo_model = YOLO(YOLO_MODEL_NAME)
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

    if u == "white":
        return c in {"white", "gray", "beige", "black"}
    if u == "black":
        return c in {"black", "gray", "white"}
    if u == "gray":
        return c in {"gray", "black", "white"}
    if u == "beige":
        return c in {"beige", "white", "brown", "gray"}

    if u in warm:
        return c in warm or c in neutral
    if u in cool:
        return c in cool or c in neutral

    return False


# ================= BODY CHECK =================
def bbox_fullbody_and_feet(img: Image.Image) -> Tuple[bool, Dict]:

def safe_crop(img: Image.Image, x1: float, y1: float, x2: float, y2: float) -> Image.Image:

    w, h = img.size
    x1 = int(clamp(int(x1), 0, w - 1))
    y1 = int(clamp(int(y1), 0, h - 1))
    x2 = int(clamp(int(x2), x1 + 1, w))
    y2 = int(clamp(int(y2), y1 + 1, h))
    return img.crop((x1, y1, x2, y2))


    boxes = r.boxes.xyxy.cpu().numpy()
    cls = r.boxes.cls.cpu().numpy()

    persons = [i for i, c in enumerate(cls) if int(c) == 0]
    if not persons:
        return False, {}

    i = max(persons, key=lambda i: (boxes[i][3]-boxes[i][1])*(boxes[i][2]-boxes[i][0]))
    x1, y1, x2, y2 = boxes[i]

    person_h = (y2 - y1) / h
    top_ratio = y1 / h
    bottom_ratio = y2 / h

    # [TUNED] 전신 기준 강화
    full_ok = person_h >= 0.78
    feet_ok = bottom_ratio >= BBOX_FEET_Y_MIN
    head_ok = top_ratio <= 0.15

    return full_ok and feet_ok and head_ok, {
        "person_h": float(person_h),
        "top_ratio": float(top_ratio),
        "bottom_ratio": float(bottom_ratio),
        "full_ok": int(full_ok),
        "feet_ok": int(feet_ok),
        "head_ok": int(head_ok),
    }

def center_square_crop(img: Image.Image, ratio: float = 0.85) -> Image.Image:
    w, h = img.size
    side = int(min(w, h) * ratio)
    cx, cy = w // 2, h // 2
    x1 = cx - side // 2
    y1 = cy - side // 2
    x2 = x1 + side
    y2 = y1 + side
    return safe_crop(img, x1, y1, x2, y2)

def ensure_tensor_features(x) -> torch.Tensor:
    """
    CLIP 관련 함수들이 버전에 따라 Tensor / BaseModelOutput / dict 등을 반환할 수 있음.
    최종적으로 (1, d) Tensor로 뽑아내기.
    """
    # 이미 텐서면 그대로
    if torch.is_tensor(x):
        return x

    # transformers 출력 객체: pooler_output / image_embeds / text_embeds / last_hidden_state 등 케이스 대응
    if hasattr(x, "image_embeds") and torch.is_tensor(x.image_embeds):
        return x.image_embeds
    if hasattr(x, "text_embeds") and torch.is_tensor(x.text_embeds):
        return x.text_embeds
    if hasattr(x, "pooler_output") and torch.is_tensor(x.pooler_output):
        return x.pooler_output
    if hasattr(x, "last_hidden_state") and torch.is_tensor(x.last_hidden_state):
        # 마지막 hidden state면 CLS 토큰(0번) 같은 대표 벡터 사용
        return x.last_hidden_state[:, 0, :]

    # dict 형태
    if isinstance(x, dict):
        for k in ("image_embeds", "text_embeds", "pooler_output", "last_hidden_state"):
            if k in x and torch.is_tensor(x[k]):
                t = x[k]
                if k == "last_hidden_state":
                    t = t[:, 0, :]
                return t

    raise TypeError(f"Cannot convert to tensor features. type={type(x)}")


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
    img = resize_max_side(img, CLIP_MAX_SIDE)

    inp = clip_processor(images=img, return_tensors="pt")
    pixel_values = inp["pixel_values"].to(device)

    # 1) 우선 get_image_features 시도
    try:
        feats = clip_model.get_image_features(pixel_values=pixel_values)
    except Exception:
        feats = None

    # 2) 어떤 타입이든 텐서로 강제
    if feats is None:
        vision_out = clip_model.vision_model(pixel_values=pixel_values)
        pooled = ensure_tensor_features(vision_out)  # pooler_output 등에서 텐서 뽑기
        feats = clip_model.visual_projection(pooled)
    else:
        feats = ensure_tensor_features(feats)

        # 만약 feats가 pooler_output(768) 같은 걸로 들어오면 projection 필요
        # (버전에 따라 get_image_features가 projection 전 벡터를 줄 수도 있어서 안전하게 처리)
        if feats.shape[-1] != clip_model.projection_dim:
            feats = clip_model.visual_projection(feats)

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


# ================= CLIP FAST (cached text embeddings) =================
_TEXT_TOK_CACHE: Dict[str, Dict[str, torch.Tensor]] = {}
_TEXT_FEAT_CACHE: Dict[str, torch.Tensor] = {}

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
        tf = None

    if tf is None:
        text_out = clip_model.text_model(**tok)
        pooled = ensure_tensor_features(text_out)
        tf = clip_model.text_projection(pooled)
    else:
        tf = ensure_tensor_features(tf)
        if tf.shape[-1] != clip_model.projection_dim:
            tf = clip_model.text_projection(tf)

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


# =========================
# HELPERS
# =========================

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

def _safe_open_image(b: bytes) -> Optional[Image.Image]:
    try:
        return Image.open(io.BytesIO(b)).convert("RGB")
    except Exception:
        return None

def _short_side(img: Image.Image) -> int:
    return min(img.size[0], img.size[1])

def dedup_candidates(cands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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



def yolo_has_any(img: Image.Image, wanted_names: List[str]) -> bool:
    if not wanted_names:
        return True
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

def apply_cfg_override(category: str, gate_cfg: Dict[str, Any], mode: str) -> Dict[str, Any]:
    cfg = dict(gate_cfg)
    ov = CATEGORY_PERSON_OVERRIDE.get(category, {}).get(mode, {})
    cfg.update(ov)
    return cfg

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


    # ✅ use proto-matched rgb (more accurate when background exists)
    keep_ratio = 0.12 if category in ("bag", "footwear") else 0.18
    rgb, dist = proto_rgb_from_region(region_img, proto, keep_ratio=keep_ratio)


    cat_kor_map = {
        "footwear": "신발",
        "top": "상의",
        "bottom": "하의",
        "outerwear": "아우터",
        "accessory": "악세사리",
    }

    base_kor_map = {
        "white t-shirt": "흰 티",
        "hoodie": "후드티",
        "jeans": "청바지",
        "coat": "코트",
        "leather dress shoes": "가죽 구두",
        "dress shoes": "구두",
        "derby shoes": "더비 구두",
        "monk strap shoes": "몽크스트랩",
        "oxford shoes": "옥스포드",
    }

    color_kor_map = {
        "beige": "베이지",
        "black": "검정",
        "white": "흰색",
        "navy": "네이비",
        "gray": "회색",
        "brown": "브라운",
    }

# ====================================================================

    # 2. 색상 추출
    COLOR_LABELS = ["black","white","gray","beige","brown","navy"]
    color_prompts = [
        f"a close-up fabric texture in {c} color" for c in COLOR_LABELS
    ] + [
        f"a fashion item mainly {c} colored" for c in COLOR_LABELS
    ]
    color_scores = clip_scores(user_img, color_prompts)

    by_color = []
    for i in range(len(COLOR_LABELS)):
        by_color.append(max(color_scores[i], color_scores[i+len(COLOR_LABELS)]))

    detected_color = COLOR_LABELS[int(torch.tensor(by_color).argmax())]
    color_kor = color_kor_map.get(detected_color, "")

# ====================================================================

    # 3. 카테고리 및 Subtype 추론
    category_prompts = list(CATEGORY_LABELS.values())
    cat_scores = clip_scores(user_img, category_prompts)
    best_idx = int(torch.tensor(cat_scores).argmax())
    cat_key = list(CATEGORY_LABELS.keys())[best_idx]
    cat_kor = cat_kor_map.get(cat_key, "패션")

    subtype_prompts = SUBTYPE_PROMPTS.get(cat_key, DEFAULT_PROMPTS)
    subtype_scores = clip_scores(user_img, subtype_prompts)
    top_idx = int(torch.tensor(subtype_scores).argmax())

    target_prompt = subtype_prompts[top_idx]
    baseLabel = target_prompt.replace("a photo of ", "")
    base = baseLabel.strip()                                  
    base_kor = base_kor_map.get(base, base)

# ====================================================================

    # [5] 아우터 디테일 (코트 길이)
    if cat_key == "outerwear":
        LENGTH_PROMPTS = ["short length", "long length", "midi length"]
        len_scores = clip_scores(user_img, [f"a {l} coat" for l in LENGTH_PROMPTS])
        detected_len = LENGTH_PROMPTS[int(torch.tensor(len_scores).argmax())]
        len_map = {
            "short length": "숏",
            "long length": "롱",
            "midi length": "미디"
        }
        base_kor = f"{len_map[detected_len]} {base_kor}"

# ====================================================================

    # [6] 검색 쿼리 생성
    korean_query = f"{color_kor} {cat_kor} {base_kor} {user_q} 전신 코디 착샷 룩북 스타일링".strip()

    naver_items = await naver_search(korean_query, display=100)
    if len(naver_items) < 20:
        wider_query = f"{base_kor} 전신 코디"
        extra_items = await naver_search(wider_query, display=50)
        naver_items.extend(extra_items)

    seen = set()
    unique = []
    for it in naver_items:
        if it["link"] not in seen:
            unique.append(it)
            seen.add(it["link"])
    naver_items = unique

# ====================================================================

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

# ====================================================================

    # [7] 사용자 이미지 feature
    user_features = get_img_features(user_img)

# ====================================================================

    # [8] 개별 이미지 처리
    async with httpx.AsyncClient(timeout=15) as client:

        async def process(it):


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

                            return None

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

                    # [ADDED] 코디(착샷) vs 상품컷 필터
                    outfit_prompts = [
                        "a full body fashion outfit",
                        "street fashion look",
                        "person wearing coordinated outfit",
                    ]
                    bad_prompts = [
                        "product only clothing",
                        "clothes on white background",
                        "advertisement banner",
                        "text poster",
                    ]
                    scores = clip_scores(img, outfit_prompts + bad_prompts)
                    outfit_score = max(scores[:3])
                    bad_score = max(scores[3:])
                    if outfit_score < bad_score + 0.08:
                        return None

                    # 3) 시각적 유사도 계산
                    cand_features = get_img_features(img)
                    visual_sim = (user_features @ cand_features.T).item()

                    # [ADDED] 너무 다른 경우 바로 제거
                    if visual_sim < 0.30:
                        return None

                    # 4) 세로형 비율 점수
                    ar = img.height / img.width
                    ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.9

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

                    # [ADDED] 아이템 확신도 낮으면 제거
                    if item_score < ITEM_TOP1_MIN_PROB:
                        return None

                    # 6) textQuery 스타일 점수 추가
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

                    # margin 계산
                    sorted_scores = sorted(match_scores, reverse=True)
                    margin = sorted_scores[0] - sorted_scores[1]

                    # 7) 스코어 계산
                    score = (
                        0.40 * visual_sim +
                        0.25 * item_score +
                        0.15 * style_score +
                        0.10 * ar_score +
                        0.10 * bbox["person_h"]

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

                    # 8) 패널티
                    penalty = 0.0
                    if margin < ITEM_MARGIN_MIN:
                        penalty += 0.10
                    if user_q and style_score < 0.12:
                        penalty += 0.05
                    if visual_sim < 0.45:
                        penalty += 0.10

                    score -= penalty

                    # 9) 젠더 점수 기록 (디버그용)
                    gender_prompts = [
                        "a full body outfit for man",
                        "a full body outfit for woman"
                    ]
                    gender_scores = clip_scores(img, gender_prompts)

                    title = (it.get("title") or "").replace("<b>", "").replace("</b>", "")

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
                        "genderScore": {
                            "man": gender_scores[0],
                            "woman": gender_scores[1]
                        }
                    }

                except Exception as e:
                    print("process error:", e)
                    return None

        processed = await asyncio.gather(*[process(it) for it in naver_items])

    # [9] 결과 정렬 및 반환
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

    print(f"{len(items)}장이 나왔습니다.")
    for i in items:
        if "genderScore" in i:
            print("최종 후보 젠더 점수:", i["genderScore"])

    top_items = items[:limit]
    for idx, it in enumerate(top_items, start=1):

    for idx, it in enumerate(final, start=1):
        it["rank"] = idx

    return {
        "requestId": requestId,
        "items": top_items,
    }

# python -m uvicorn main:app --reload
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug
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
