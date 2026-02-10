from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import io
import time
import asyncio
import traceback
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, Optional, List, Tuple

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

import httpx
import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

from ultralytics import YOLO

# ================= ENV =================
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ================= CONFIG =================
MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# Kakao optional
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

# OpenAI optional (for /chat)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Search sources
SEARCH_SOURCES = [
    s.strip().lower()
    for s in os.getenv("SEARCH_SOURCES", "naver,kakao").split(",")
    if s.strip()
]

# ========= Gates / thresholds =========
# Full-body gates (STRICT default)
PORTRAIT_AR_MIN = 1.02
BBOX_FEET_Y_MIN = 0.86
PERSON_H_MIN = 0.70
HEAD_TOP_MAX = 0.15
MULTI_PERSON_MAX = 1

# item gate
ITEM_REGION_MIN_PROB = 0.20
ITEM_REGION_MARGIN_MIN = 0.02
ITEM_VS_PRODUCT_MIN_MARGIN = 0.03

# pose gate
POSE_GATE_STRICT = False
POSE_GATE_PENALTY = 0.10

# screenshot/product gate
OUTFIT_BAD_MARGIN = 0.00
OUTFIT_ABS_MIN = 0.52

# speed
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "6"))
FINAL_LIMIT_DEFAULT = int(os.getenv("FINAL_LIMIT_DEFAULT", "8"))

# Speed: cap candidate pool early
RAW_POOL_LIMIT = int(os.getenv("RAW_POOL_LIMIT", "220"))

# CLIP speed: resize before inference
CLIP_MAX_SIDE = int(os.getenv("CLIP_MAX_SIDE", "640"))
MIN_SHORT_SIDE = int(os.getenv("MIN_SHORT_SIDE", "480"))

# Color policy
COLOR_STRICT_DEFAULT = os.getenv("COLOR_STRICT_DEFAULT", "true").lower() == "true"
COLOR_FALLBACK_COMPAT = os.getenv("COLOR_FALLBACK_COMPAT", "true").lower() == "true"
COLOR_STRICT_IF_CONF_GE = float(os.getenv("COLOR_STRICT_IF_CONF_GE", "0.45"))

# Gender policy (for /api/v1 endpoint)
GENDER_MARGIN_DEFAULT = float(os.getenv("GENDER_MARGIN", "0.03"))

# ================= APP =================
app = FastAPI(title="Styling Recommend API (Dual Endpoint, Clean)")

# (Optional) CORS - allow local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    print("\n=== UNHANDLED ERROR ===")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": repr(exc)})

# ================= MODELS =================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("[BOOT] DEVICE =", DEVICE)

clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# YOLO
yolo_person = YOLO(os.getenv("YOLO_PERSON_WEIGHTS", "yolov8n.pt"))
yolo_pose = YOLO(os.getenv("YOLO_POSE_WEIGHTS", "yolov8n-pose.pt"))
YOLO_NAMES = (
    yolo_person.model.names
    if hasattr(yolo_person, "model") and hasattr(yolo_person.model, "names")
    else {}
)

# rembg (optional)
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


def normalize_gender(g: str) -> str:
    """Normalize gender inputs from UI/clients.

    Accepts: male/female, man/woman, and common Korean variants.
    Returns: 'male', 'female', or '' (unknown/unset).
    """
    s = (g or "").strip().lower()
    if s in ("male", "man", "m", "남", "남자", "남성"):
        return "male"
    if s in ("female", "woman", "f", "w", "여", "여자", "여성"):
        return "female"
    return ""

def looks_like_image_contenttype(ct: str) -> bool:
    return (ct or "").lower().startswith("image/")

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

# ================= CLIP (fast text cache) =================
_TEXT_TOK_CACHE: Dict[str, Dict[str, torch.Tensor]] = {}
_TEXT_FEAT_CACHE: Dict[str, torch.Tensor] = {}

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
def get_text_features_cached(prompt: str) -> torch.Tensor:
    p = prompt.strip()
    if p in _TEXT_FEAT_CACHE:
        return _TEXT_FEAT_CACHE[p]
    if p not in _TEXT_TOK_CACHE:
        tok = clip_processor.tokenizer([p], padding=True, truncation=True, return_tensors="pt")
        _TEXT_TOK_CACHE[p] = {k: v.cpu() for k, v in tok.items()}
    tok = {k: v.to(DEVICE) for k, v in _TEXT_TOK_CACHE[p].items()}
    try:
        tf = clip_model.get_text_features(**tok)
    except Exception:
        text_out = clip_model.text_model(**tok)
        pooled = text_out.pooler_output
        tf = clip_model.text_projection(pooled)
    tf = _to_tensor(tf)
    tf = tf / tf.norm(dim=-1, keepdim=True)
    _TEXT_FEAT_CACHE[p] = tf.detach()
    return _TEXT_FEAT_CACHE[p]

@torch.inference_mode()
def get_img_features(img: Image.Image) -> torch.Tensor:
    img = resize_max_side(img, CLIP_MAX_SIDE)
    inp = clip_processor(images=img, return_tensors="pt")
    pixel_values = inp["pixel_values"].to(DEVICE)
    try:
        feats = clip_model.get_image_features(pixel_values=pixel_values)
    except Exception:
        vision_out = clip_model.vision_model(pixel_values=pixel_values)
        pooled = vision_out.pooler_output
        feats = clip_model.visual_projection(pooled)
    feats = _to_tensor(feats)
    if feats.ndim == 1:
        feats = feats.unsqueeze(0)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats

@torch.inference_mode()
def clip_scores_fast(img: Image.Image, prompts: List[str]) -> List[float]:
    img_feat = get_img_features(img)  # [1,d]
    tfs = torch.cat([get_text_features_cached(p) for p in prompts], dim=0)  # [n,d]
    scale = clip_model.logit_scale.exp() if hasattr(clip_model, "logit_scale") else 1.0
    logits = (img_feat @ tfs.T) * scale
    probs = logits.softmax(dim=1)[0]
    return probs.detach().cpu().tolist()

# ================= COLOR (fast RGB + optional rembg LAB) =================
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

def rembg_alpha(img_rgb: Image.Image) -> np.ndarray:
    if not REMBG_OK:
        raise RuntimeError("rembg not available")
    buf = io.BytesIO()
    img_rgb.save(buf, format="PNG")
    out_bytes = rembg_remove(buf.getvalue())
    out_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    alpha = np.asarray(out_img.split()[-1], dtype=np.float32) / 255.0
    return alpha

def dominant_color_label_rembg_lab(img_rgb: Image.Image) -> Tuple[str, float]:
    """Accurate color (best): rembg fg median in LAB -> prototype distance (fallback to fast)."""
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
    return (cand == user_color) or color_compatible(user_color, cand)

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

def bbox_fullbody_gate(img: Image.Image, *, require_feet: bool) -> Tuple[bool, Dict[str, Any]]:
    w, h = img.size
    bbox, person_count = yolo_best_person_bbox(img)
    if bbox is None:
        return False, {"person_count": 0}
    x1, y1, x2, y2 = bbox
    person_h = (y2 - y1) / max(1, h)
    top_ratio = y1 / max(1, h)
    bottom_ratio = y2 / max(1, h)

    full_ok = person_h >= PERSON_H_MIN
    feet_ok = (bottom_ratio >= BBOX_FEET_Y_MIN) if require_feet else True
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
        pts = xy[i]; c = conf[i]
        m = c > 0.2
        if m.sum() < 4:
            return 0.0
        p = pts[m]
        return float((p[:, 0].max() - p[:, 0].min()) * (p[:, 1].max() - p[:, 1].min()))

    best_i = max(range(n), key=area_of)
    pts = xy[best_i]
    cfs = conf[best_i]

    # COCO: nose=0, left_ankle=15, right_ankle=16
    if cfs[0] <= 0.20:
        return False, {"pose": "nose_missing"}
    la_ok = cfs[15] > 0.20
    ra_ok = cfs[16] > 0.20
    if not (la_ok or ra_ok):
        return False, {"pose": "ankle_missing"}

    nose_y = float(pts[0, 1] / max(1, h))
    ankle_y = float((max(pts[15, 1], pts[16, 1]) if (la_ok and ra_ok) else (pts[15, 1] if la_ok else pts[16, 1])) / max(1, h))

    head_ok = nose_y <= 0.22
    feet_ok = ankle_y >= 0.90
    ok = head_ok and feet_ok
    return ok, {"nose_y": round(nose_y, 4), "ankle_y": round(ankle_y, 4), "head_ok": int(head_ok), "feet_ok": int(feet_ok)}

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
    crops: List[Image.Image] = [crop_region_by_part(person_crop, part)]
    if part == "feet":
        crops += [
            safe_crop(person_crop, 0, h * 0.62, w, h * 1.00),
            safe_crop(person_crop, w * 0.08, h * 0.65, w * 0.92, h * 1.00),
        ]
    elif part == "hands":
        crops += [
            safe_crop(person_crop, 0, h * 0.18, w, h * 0.95),
            safe_crop(person_crop, w * 0.05, h * 0.15, w * 0.95, h * 0.92),
        ]
    elif part == "upper":
        crops += [
            safe_crop(person_crop, 0, h * 0.05, w, h * 0.65),
            safe_crop(person_crop, w * 0.06, h * 0.08, w * 0.94, h * 0.62),
        ]
    elif part == "lower":
        crops += [
            safe_crop(person_crop, 0, h * 0.35, w, h * 1.00),
            safe_crop(person_crop, w * 0.06, h * 0.42, w * 0.94, h * 0.98),
        ]
    else:
        crops += [safe_crop(person_crop, 0, h * 0.05, w, h * 0.95)]
    crops.append(center_square_crop(person_crop, 0.72))
    return [c for c in crops if short_side(c) >= 160]

# ================= TAXONOMY (ANY ITEM) =================
ITEM_TAXONOMY: List[Dict[str, Any]] = [
    # shoes
    {"en": "sneakers", "kr": ["운동화", "스니커즈"], "part": "feet", "yolo_classes": []},
    {"en": "boots", "kr": ["부츠"], "part": "feet", "yolo_classes": []},
    {"en": "loafers", "kr": ["로퍼"], "part": "feet", "yolo_classes": []},
    {"en": "dress shoes", "kr": ["구두", "드레스슈즈"], "part": "feet", "yolo_classes": []},
    {"en": "sandals", "kr": ["샌들"], "part": "feet", "yolo_classes": []},
    {"en": "slippers", "kr": ["슬리퍼"], "part": "feet", "yolo_classes": []},

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
    return [f"a photo of {x['en']}" for x in ITEM_TAXONOMY]

def taxonomy_best(user_crop: Image.Image) -> Tuple[Dict[str, Any], float]:
    prompts = taxonomy_prompts()
    scores = clip_scores_fast(user_crop, prompts)
    idx = int(torch.tensor(scores).argmax())
    best_item = ITEM_TAXONOMY[idx]
    best_prob = float(scores[idx])
    return best_item, best_prob

def find_taxonomy_by_category(category: str) -> Optional[Dict[str, Any]]:
    c = (category or "").strip().lower()
    if not c:
        return None
    # Map "top/bottom/bag/footwear/outerwear/dress/skirt" style categories
    # into a representative taxonomy entry (used only as hint for prompts/part)
    if c in ("footwear", "shoes", "shoe", "sneakers", "boots", "loafers", "sandals", "slippers"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "sneakers"), None)
    if c in ("bag", "backpack", "handbag"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "handbag"), None)
    if c in ("outerwear", "coat", "jacket", "outer"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "long coat"), None)
    if c in ("dress", "onepiece"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "dress"), None)
    if c in ("bottom", "pants", "trousers", "jeans", "slacks", "skirt"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "jeans"), None)
    if c in ("top", "tops", "shirt", "t-shirt", "hoodie", "knit"):
        return next((x for x in ITEM_TAXONOMY if x["en"] == "t-shirt"), None)
    return None

def category_requires_feet(category: str) -> bool:
    c = (category or "").strip().lower()
    return c in ("footwear", "shoes", "shoe", "sneakers", "boots", "loafers", "sandals", "slippers")

def category_allows_no_feet(category: str) -> bool:
    # For bag/outerwear/top/bottom/dress we allow 3/4-ish (feet not required)
    return not category_requires_feet(category)

# ================= SEARCH: NAVER + KAKAO =================
async def naver_search_once(query: str, display: int = 80, start: int = 1) -> List[Dict[str, Any]]:
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET):
        return []
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
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url, headers=headers, params=params)
            print("[NAVER]", r.status_code, "|", query)
            if r.status_code != 200:
                print("[NAVER ERR]", r.text[:300])
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
    except Exception as e:
        print("[NAVER ERROR]", repr(e))
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
    try:
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
                })
            return out
    except Exception as e:
        print("[KAKAO ERROR]", repr(e))
        return []

def merge_dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("link") or "")[:400]
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

async def search_multi_sources(queries: List[str], *, naver_each: int = 80, kakao_each: int = 80) -> List[Dict[str, Any]]:
    tasks = []
    for q in queries:
        if "naver" in SEARCH_SOURCES:
            tasks.append(naver_search_once(q, display=naver_each, start=1))
        if "kakao" in SEARCH_SOURCES:
            tasks.append(kakao_search_once(q, size=kakao_each, page=1))

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

# ================= YOLO OBJECT GATE (optional) =================
def yolo_has_any(img: Image.Image, wanted_names: List[str]) -> bool:
    if not wanted_names:
        return True
    r = yolo_person.predict(img, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return False
    cls = r.boxes.cls.cpu().numpy().astype(int).tolist()
    present = set(YOLO_NAMES.get(i, "") for i in cls)
    return any(w in present for w in wanted_names)

# ================= PROMPTS (separation) =================
def outfit_gate_prompts() -> List[str]:
    # Keep this small for speed; strong separation between outfit vs product/screenshot.
    return [
        "a full body street fashion outfit photo",
        "a street style outfit photo",
        "a product photo of an item",
        "a screenshot of a shopping webpage",
    ]

def choose_distractors(item_en: str, item_part: str) -> List[str]:
    if item_part == "feet":
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
    dist = [f"a full body street fashion photo of a person wearing {d}" for d in [x for x in distractors if x != item_en][:4]]
    return targets + bads + dist

def gender_prompts() -> Tuple[List[str], List[str]]:
    male = [
        "a full body street fashion outfit photo of a man",
        "a man wearing a street style outfit",
        "menswear outfit full body photo",
    ]
    female = [
        "a full body street fashion outfit photo of a woman",
        "a woman wearing a street style outfit",
        "womenswear outfit full body photo",
    ]
    return male, female

# ================= CORE PIPELINE =================
async def run_anyitem_pipeline(
    *,
    user_img: Image.Image,
    user_q: str,
    limit: int,
    source_request_id: str,
) -> Dict[str, Any]:
    """Core pipeline used by /recommend/image (auto taxonomy)."""
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

    # 2) user item crop + color + features
    if user_person_crop is not None:
        user_item_crop = crop_region_by_part(user_person_crop, item_part)
    else:
        user_item_crop = center_square_crop(user_img, 0.85)

    user_color, user_color_conf = dominant_color_label_rembg_lab(user_item_crop)
    user_item_features = get_img_features(user_item_crop)

    # 3) queries
    color_kor = COLOR_KOR.get(user_color, "")
    item_kor = item_kr_list[0] if item_kr_list else "패션"

    q1 = f"{color_kor} {item_kor} 전신 착샷 코디 룩북 무신사 스냅 OOTD 착용 {user_q}".strip()
    q2 = f"{color_kor} {item_kor} 데일리룩 스트릿 스냅 전신 코디 착용 {user_q}".strip()
    q3 = f"{item_kor} 전신 코디 착샷 룩북 무신사 스냅 착용 {user_q}".strip()
    q4 = f"{item_kor} 코디 전신 OOTD 스트릿룩 착용 {user_q}".strip()
    queries = [q1, q2, q3, q4]

    candidates = await search_multi_sources(queries, naver_each=80, kakao_each=80)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:

        async def process(it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with sem:
                try:
                    async with asyncio.timeout(CANDIDATE_TIMEOUT_SEC):
                        url = it.get("link")
                        if not url:
                            await drop("no_url"); return None

                        r = await client.get(url)
                        if r.status_code != 200:
                            await drop("download_fail"); return None

                        ct = r.headers.get("content-type", "")
                        if not looks_like_image_contenttype(ct):
                            await drop("not_image_contenttype"); return None

                        try:
                            img = pil_rgb(r.content)
                        except Exception:
                            await drop("decode_fail"); return None

                        if short_side(img) < MIN_SHORT_SIDE:
                            await drop("too_small"); return None

                        # fullbody strict: require feet? depends on item_part (feet item -> require feet)
                        require_feet = (item_part == "feet")
                        ok_bbox, bbox = bbox_fullbody_gate(img, require_feet=require_feet)
                        if not ok_bbox:
                            await drop("bbox_fullbody_fail"); return None

                        ok_pose, pose_meta = pose_fullbody_gate(img)
                        if POSE_GATE_STRICT and (not ok_pose):
                            await drop("pose_fullbody_fail"); return None

                        # outfit vs bad
                        gs = clip_scores_fast(img, outfit_gate_prompts())
                        outfit_score = float(gs[0])
                        bad_score = float(max(gs[2:]))
                        if not (outfit_score > bad_score + OUTFIT_BAD_MARGIN or outfit_score >= OUTFIT_ABS_MIN):
                            await drop("screenshot_or_product"); return None

                        pb = bbox.get("bbox")
                        if not pb:
                            await drop("bbox_missing"); return None
                        person_crop = safe_crop(img, pb[0], pb[1], pb[2], pb[3])

                        # optional YOLO object gate
                        if yolo_gate_classes and not yolo_has_any(person_crop, yolo_gate_classes):
                            await drop("yolo_object_missing"); return None

                        crops = multi_crops_for_part(person_crop, item_part)

                        # item presence
                        distractors = choose_distractors(item_en, item_part)
                        prompts = item_presence_prompts(item_en, user_color, distractors)

                        best_local = -1e9
                              # Fallback (if strict fast-color filter blocks everything)
                        best_local = -1e9
                        best_margin12 = -1e9
                        best_margin_vs_bad = -1e9
                        best_crop = None
                        best_rs: Optional[List[float]] = None
                        best_t_best_real = 0.0

                        # Fallback (if fast color prefilter blocks everything)
                        fb_local = -1e9
                        fb_margin12 = -1e9
                        fb_margin_vs_bad = -1e9
                        fb_crop = None
                        fb_t_best_real = 0.0

                        for c in crops:
                            color_blocked = False
                            if COLOR_STRICT_DEFAULT and not fast_color_distance_ok(user_color, c):
                                color_blocked = True

                            rs = clip_scores_fast(c, prompts)
                            t_best = float(max(rs[0:3]))
                            b_best = float(max(rs[3:6]))
                            margin_vs_bad = float(t_best - b_best)
                            srt = sorted(rs, reverse=True)
                            margin12 = float(srt[0] - srt[1]) if len(srt) >= 2 else 0.0

                            local = 0.70 * t_best + 0.30 * margin_vs_bad

                            if color_blocked:
                                if local > fb_local:
                                    fb_local = local
                                    fb_margin12 = margin12
                                    fb_margin_vs_bad = margin_vs_bad
                                    fb_crop = c
                                    fb_t_best_real = t_best
                                continue

                            if local > best_local:
                                best_local = local
                                best_margin12 = margin12
                                best_margin_vs_bad = margin_vs_bad
                                best_crop = c
                                best_rs = rs
                                best_t_best_real = t_best

                        if best_crop is None and fb_crop is not None:
                            # Fallback: allow candidates blocked by fast color prefilter
                            best_crop = fb_crop
                            best_local = fb_local
                            best_margin12 = fb_margin12
                            best_margin_vs_bad = fb_margin_vs_bad
                            best_rs = None  # keep None; we only need best_t_best_real/margins
                            best_t_best_real = fb_t_best_real

                        if best_crop is None:
                            await drop("item_crop_fail")
                            return None

                        used_color_prefilter_fallback = int(best_crop is fb_crop)

                        if best_t_best_real < ITEM_REGION_MIN_PROB:
                            await drop("item_region_low"); return None
                        if best_margin12 < ITEM_REGION_MARGIN_MIN:
                            await drop("item_region_ambiguous"); return None
                        if best_margin_vs_bad < ITEM_VS_PRODUCT_MIN_MARGIN:
                            await drop("item_vs_product_ambiguous"); return None

                        # color strict (accurate)
                        cand_color, cand_color_conf = dominant_color_label_rembg_lab(best_crop)
                        strict_allowed = (user_color_conf >= COLOR_STRICT_IF_CONF_GE) and (cand_color_conf >= COLOR_STRICT_IF_CONF_GE)
                        strict_ok = (cand_color == user_color) if user_color else True
                        compat_ok = color_compatible(user_color, cand_color) if user_color else True

                        if COLOR_STRICT_DEFAULT and strict_allowed and not strict_ok:
                            await drop("color_strict_mismatch"); return None
                        if (not strict_allowed) and COLOR_FALLBACK_COMPAT and (not (strict_ok or compat_ok)):
                            await drop("color_compat_mismatch"); return None

                        # similarity
                        cand_item_features = get_img_features(best_crop)
                        visual_sim = float((user_item_features @ cand_item_features.T).item())

                        ar = img.height / max(1, img.width)
                        ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.90

                        style_score = 0.0
                        if user_q:
                            style_prompts = [
                                f"a full body {user_q} outfit photo",
                                f"a {user_q} street fashion lookbook",
                                f"a fashion style of {user_q}",
                            ]
                            style_score = float(max(clip_scores_fast(person_crop, style_prompts)))

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

                        return {
                            "imageUrl": url,
                            "landingUrl": it.get("originallink") or url,
                            "thumbUrl": it.get("thumbnail") or url,
                            "title": it.get("title") or "",
                            "source": it.get("_source", "unknown"),
                            "score": clamp(score, 0, 2),
                            "meta": {
                                "user_mode": user_mode,
                                "detected_item_en": item_en,
                                "detected_item_prob": round(best_prob, 4),
                                "item_part": item_part,
                                "user_color": user_color,
                                "user_color_conf": round(float(user_color_conf), 4),
                                "cand_color": cand_color,
                                "cand_color_conf": round(float(cand_color_conf), 4),
                                "color_prefilter_fallback_used": int(used_color_prefilter_fallback),
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
                            }
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
        "requestId": source_request_id,
        "items": final,
        "debug": {
            "detected": {
                "user_mode": user_mode,
                "item_en": item_en,
                "item_kr": item_kor,
                "item_prob": round(best_prob, 4),
                "user_color": user_color,
                "user_color_conf": round(float(user_color_conf), 4),
                "queries": queries,
                "sources": {"naver": ("naver" in SEARCH_SOURCES), "kakao": ("kakao" in SEARCH_SOURCES and bool(KAKAO_REST_API_KEY))},
                "part": item_part,
            },
            "rawCount": len(candidates),
            "passCount": len(items),
            "finalCount": len(final),
            "drop_counts": dict(sorted(drop_counts.items(), key=lambda kv: kv[1], reverse=True)),
        }
    }

async def run_strictloose_wrapper(
    *,
    item_img: Image.Image,
    text_query: str,
    category: str,
    gender: str,
    user_color_raw: str,
    limit: int,
) -> Dict[str, Any]:
    """
    Keep your /api/v1 behavior but without dragging old broken code:
    - Uses same core scoring & gates.
    - STRICT first, if 0 results -> LOOSE relaxes: feet not required for non-footwear, color compat allowed, lower thresholds a bit.
    - Gender adds soft filter.
    """
    warnings: List[str] = []
    request_id = f"ui-{int(time.time()*1000)}"
    user_q = (text_query or "").strip()

    # Decide target item hint from category if provided, else taxonomy from image
    cat_hint = find_taxonomy_by_category(category)
    if cat_hint is not None:
        item_en = cat_hint["en"]
        item_part = cat_hint["part"]
        item_kr = (cat_hint["kr"][0] if cat_hint.get("kr") else "패션")
        best_prob = 1.0
        warnings.append(f"Category hint used: {category} -> {item_en}")
    else:
        best_item, best_prob = taxonomy_best(center_square_crop(item_img, 0.85))
        item_en = best_item["en"]
        item_part = best_item["part"]
        item_kr = (best_item["kr"][0] if best_item.get("kr") else "패션")
        warnings.append(f"Category not provided -> inferred item: {item_en} ({best_prob:.3f})")

    # user_color: use provided or infer from item image
    user_color = (user_color_raw or "").strip().lower()
    if user_color and user_color not in COLOR_LABELS:
        warnings.append(f"userColor '{user_color_raw}' not in supported labels {COLOR_LABELS} -> ignored")
        user_color = ""

    if not user_color:
        user_color, user_color_conf = dominant_color_label_rembg_lab(center_square_crop(item_img, 0.85))
        warnings.append(f"Color inferred from item image: {user_color} (conf={user_color_conf:.2f})")
    else:
        user_color_conf = 1.0
        warnings.append(f"Color provided: {user_color}")

    # Build queries (Korean-first, same style as your code)
    color_kor = COLOR_KOR.get(user_color, "")
    q1 = f"{color_kor} {item_kr} 전신 착샷 코디 룩북 무신사 스냅 OOTD 착용 {user_q}".strip()
    q2 = f"{color_kor} {item_kr} 데일리룩 스트릿 스냅 전신 코디 착용 {user_q}".strip()
    q3 = f"{item_kr} 전신 코디 착샷 룩북 무신사 스냅 착용 {user_q}".strip()
    q4 = f"{item_kr} 코디 전신 OOTD 스트릿룩 착용 {user_q}".strip()
    queries = [q1, q2, q3, q4]

    candidates = await search_multi_sources(queries, naver_each=80, kakao_each=80)

    # Features from item image (same logic)
    user_item_features = get_img_features(center_square_crop(item_img, 0.85))

    # gender prompts
    gender_raw_in = gender
    gender = normalize_gender(gender)
    male_prompts, female_prompts = gender_prompts()
    use_gender = gender in ("male", "female")

    async def run_mode(mode: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        drop_counts = defaultdict(int)
        drop_lock = asyncio.Lock()
        async def drop(reason: str):
            async with drop_lock:
                drop_counts[reason] += 1

        # relax settings for loose
        require_feet = category_requires_feet(category)
        if mode == "LOOSE" and category_allows_no_feet(category):
            require_feet = False

        # looser thresholds
        item_prob_min = ITEM_REGION_MIN_PROB if mode == "STRICT" else max(0.14, ITEM_REGION_MIN_PROB - 0.06)
        margin12_min = ITEM_REGION_MARGIN_MIN if mode == "STRICT" else max(0.00, ITEM_REGION_MARGIN_MIN - 0.02)
        margin_vs_bad_min = ITEM_VS_PRODUCT_MIN_MARGIN if mode == "STRICT" else max(0.00, ITEM_VS_PRODUCT_MIN_MARGIN - 0.03)

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            async def process(it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                async with sem:
                    try:
                        url = it.get("link")
                        if not url:
                            await drop("no_url"); return None
                        r = await client.get(url)
                        if r.status_code != 200:
                            await drop("download_fail"); return None
                        ct = r.headers.get("content-type", "")
                        if not looks_like_image_contenttype(ct):
                            await drop("not_image_contenttype"); return None
                        try:
                            img = pil_rgb(r.content)
                        except Exception:
                            await drop("decode_fail"); return None
                        if short_side(img) < MIN_SHORT_SIDE:
                            await drop("too_small"); return None

                        ok_bbox, bbox = bbox_fullbody_gate(img, require_feet=require_feet)
                        if not ok_bbox:
                            await drop("bbox_fullbody_fail"); return None

                        ok_pose, pose_meta = pose_fullbody_gate(img)
                        if POSE_GATE_STRICT and (not ok_pose):
                            await drop("pose_fullbody_fail"); return None

                        gs = clip_scores_fast(img, outfit_gate_prompts())
                        outfit_score = float(gs[0])
                        bad_score = float(max(gs[2:]))
                        if mode == "STRICT":
                            ok_outfit = (outfit_score > bad_score + OUTFIT_BAD_MARGIN) or (outfit_score >= OUTFIT_ABS_MIN)
                        else:
                            ok_outfit = (outfit_score > bad_score - 0.02) or (outfit_score >= (OUTFIT_ABS_MIN - 0.04))
                        if not ok_outfit:
                            await drop("screenshot_or_product"); return None

                        pb = bbox.get("bbox")
                        person_crop = safe_crop(img, pb[0], pb[1], pb[2], pb[3])

                        # item presence on region crops
                        crops = multi_crops_for_part(person_crop, item_part)
                        distractors = choose_distractors(item_en, item_part)
                        prompts = item_presence_prompts(item_en, user_color, distractors)

                        best_local = -1e9
                        best_margin12 = -1e9
                        best_margin_vs_bad = -1e9
                        best_crop = None
                        best_t_best_real = 0.0

                        for c in crops:
                            if mode == "STRICT" and COLOR_STRICT_DEFAULT and not fast_color_distance_ok(user_color, c):
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
                                best_t_best_real = t_best

                        if best_crop is None:
                            await drop("item_crop_fail"); return None

                        if best_t_best_real < item_prob_min:
                            await drop("item_region_low"); return None
                        if best_margin12 < margin12_min:
                            await drop("item_region_ambiguous"); return None
                        if best_margin_vs_bad < margin_vs_bad_min:
                            await drop("item_vs_product_ambiguous"); return None

                        cand_color, cand_color_conf = dominant_color_label_rembg_lab(best_crop)

                        strict_allowed = (user_color_conf >= COLOR_STRICT_IF_CONF_GE) and (cand_color_conf >= COLOR_STRICT_IF_CONF_GE)
                        strict_ok = (cand_color == user_color) if user_color else True
                        compat_ok = color_compatible(user_color, cand_color) if user_color else True

                        if mode == "STRICT":
                            if COLOR_STRICT_DEFAULT and strict_allowed and not strict_ok:
                                await drop("color_strict_mismatch"); return None
                        else:
                            # loose: allow compat when uncertain
                            if user_color and (not (strict_ok or compat_ok)):
                                await drop("color_compat_mismatch"); return None

                        cand_item_features = get_img_features(best_crop)
                        visual_sim = float((user_item_features @ cand_item_features.T).item())

                        # gender soft filter
                        gender_bonus = 0.0
                        male_s = female_s = 0.0
                        if use_gender:
                            male_s = float(max(clip_scores_fast(img, male_prompts)))
                            female_s = float(max(clip_scores_fast(img, female_prompts)))
                            if gender == "male":
                                if (male_s - female_s) < (GENDER_MARGIN_DEFAULT if mode == "STRICT" else max(0.0, GENDER_MARGIN_DEFAULT - 0.02)):
                                    await drop("gender_fail"); return None
                                gender_bonus = max(0.0, male_s - female_s)
                            else:
                                if (female_s - male_s) < (GENDER_MARGIN_DEFAULT if mode == "STRICT" else max(0.0, GENDER_MARGIN_DEFAULT - 0.02)):
                                    await drop("gender_fail"); return None
                                gender_bonus = max(0.0, female_s - male_s)

                        ar = img.height / max(1, img.width)
                        ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.90

                        style_score = 0.0
                        if user_q:
                            style_prompts = [
                                f"a full body {user_q} outfit photo",
                                f"a {user_q} street fashion lookbook",
                                f"a fashion style of {user_q}",
                            ]
                            style_score = float(max(clip_scores_fast(person_crop, style_prompts)))

                        score = (
                            0.46 * visual_sim +
                            0.24 * best_t_best_real +
                            0.10 * best_margin_vs_bad +
                            0.06 * style_score +
                            0.05 * ar_score +
                            0.05 * float(bbox.get("person_h", 0.0)) +
                            0.04 * float(gender_bonus) +
                            0.00 * float(outfit_score)
                        )
                        if not ok_pose:
                            score -= POSE_GATE_PENALTY

                        return {
                            "rankScore": float(score),
                            "imageUrl": url,
                            "imageUrlDirect": url,
                            "landingUrl": it.get("originallink") or url,
                            "thumbUrl": it.get("thumbnail") or url,
                            "source": it.get("_source", "unknown"),
                            "debug": {
                                "mode": mode,
                                "item_en": item_en,
                                "item_part": item_part,
                                "posOutfit": outfit_score,
                                "negBad": bad_score,
                                "t_best": best_t_best_real,
                                "margin_vs_bad": best_margin_vs_bad,
                                "margin_12": best_margin12,
                                "visual_sim": visual_sim,
                                "user_color": user_color,
                                "cand_color": cand_color,
                                "bbox": bbox,
                                "pose": pose_meta,
                                "gender": {"wanted": gender, "male": male_s, "female": female_s, "bonus": gender_bonus},
                            }
                        }
                    except Exception:
                        await drop("process_exception")
                        return None

            processed = await asyncio.gather(*[process(it) for it in candidates])

        ok_items = [x for x in processed if x]
        return ok_items, dict(sorted(drop_counts.items(), key=lambda kv: kv[1], reverse=True))

    ok_items, drop_strict = await run_mode("STRICT")
    gate_used = "strict"
    if len(ok_items) == 0:
        gate_used = "loose"
        warnings.append("No results in STRICT -> fallback to LOOSE.")
        ok_items, drop_loose = await run_mode("LOOSE")
    else:
        drop_loose = {}

    ok_items.sort(key=lambda x: x.get("rankScore", 0.0), reverse=True)
    items_out = []
    for i, it in enumerate(ok_items[: min(int(limit or FINAL_LIMIT_DEFAULT), 20)], start=1):
        items_out.append({
            "rank": i,
            "rankScore": it["rankScore"],
            "imageUrl": it.get("imageUrl"),
            "imageUrlDirect": it.get("imageUrlDirect") or it.get("imageUrl"),
            "landingUrl": it.get("landingUrl") or it.get("imageUrlDirect") or it.get("imageUrl"),
            "thumbUrl": it.get("thumbUrl") or it.get("imageUrl"),
            "source": it.get("source"),
            "debug": it.get("debug", {}),
        })

    return {
        "query": " / ".join(queries[:2]),
        "category": category,
        "gender": gender,
        "userColor": user_color_raw,
        "normalizedColor": user_color,
        "gateUsed": gate_used,
        "rawCount": {"deduped": len(candidates)},
        "itemsCount": len(items_out),
        "items": items_out,
        "sources": SEARCH_SOURCES,
        "device": DEVICE,
        "warnings": warnings,
        "requestId": request_id,
        "received": {
            "requestId": request_id,
            "query": user_q,
            "category_raw": category,
            "gender_raw": gender_raw_in,
            "userColor_raw": user_color_raw,
            "normalizedColor": user_color,
            "policy": {
                "dual_endpoint": True,
                "strict_then_loose": True,
                "footwear_requires_feet": True,
                "loose_allows_no_feet_for_non_footwear": True,
                "clip_text_cache": True,
                "color_method": "rembg_lab_or_fast_rgb",
            },
        },
        "debug": {
            "drop_counts_strict": drop_strict,
            "drop_counts_loose": drop_loose,
        }
    }

# =========================
# API: ANY-ITEM (your newer endpoint)
# =========================
@app.post("/recommend/image")
async def recommend_image_anyitem(
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    requestId: str = Form(...),
    textQuery: str = Form(""),
):
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET) and ("naver" in SEARCH_SOURCES):
        return {"error": "NAVER_CLIENT_ID/SECRET 없음"}
    user_img = pil_rgb(await image.read())
    user_q = (textQuery or "").strip()
    out = await run_anyitem_pipeline(user_img=user_img, user_q=user_q, limit=int(limit), source_request_id=requestId)
    return out

# =========================
# API: STRICT/LOOSE (compat endpoint for your front)
# =========================
@app.post("/api/v1/recommend/image")
async def recommend_image_strictloose(
    image: UploadFile = File(...),
    limit: int = Form(FINAL_LIMIT_DEFAULT),
    textQuery: str = Form(""),
    category: str = Form(""),
    gender: str = Form(""),
    userColor: str = Form(""),
):
    if not (NAVER_CLIENT_ID and NAVER_CLIENT_SECRET) and ("naver" in SEARCH_SOURCES):
        return JSONResponse({"error": "NAVER_CLIENT_ID/SECRET 없음"}, status_code=400)
    item_img = pil_rgb(await image.read())
    return await run_strictloose_wrapper(
        item_img=item_img,
        text_query=textQuery,
        category=category,
        gender=gender,
        user_color_raw=userColor,
        limit=int(limit),
    )

# =========================
# API: LLM CHAT (OpenAI Responses API) - kept from your logic
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

# 실행:
# python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug
