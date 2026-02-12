from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import requests
import random
from transformers import CLIPProcessor, CLIPModel
from io import BytesIO

app = FastAPI(
    title="AI Outfit Codynate API",
    description="이미지 기반 코디 추천 서비스",
)

# 서버 실행:
# uvicorn app:app --reload

# =========================
# CLIP 모델 로드
# =========================

MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

print("CLIP 모델 로드 완료")

# =========================
# 카테고리별 라벨 
# =========================

CANDIDATE_LABELS = {
    "outer": [
        "beige trench coat",
        "beige long coat",
        "beige wool coat",
        "camel coat",
        "oversized coat",
        "long outerwear",
        "light coat",
        "winter coat",
        "padded jacket",
        "down jacket",
        "short jacket",
        "leather jacket",
        "denim jacket",
        "blazer",
        "cardigan",
        "hooded jacket",
        "field jacket",
        "parka"
    ],
    "top": [
        "white t-shirt",
        "black t-shirt",
        "striped shirt",
        "dress shirt",
        "black hoodie",
        "oversized hoodie",
        "knit sweater",
        "turtleneck",
        "cardigan",
        "sweatshirt",
        "crop top",
        "long sleeve shirt"
    ],
    "bottom": [
        "light blue jeans",
        "dark blue jeans",
        "black jeans",
        "slacks",
        "wide pants",
        "cargo pants",
        "pleated pants",
        "mini skirt",
        "long skirt",
        "denim skirt",
        "shorts"
    ],
    "shoes": [
        "sneakers",
        "running shoes",
        "loafers",
        "derby shoes",
        "ankle boots",
        "combat boots",
        "sandals",
        "heels",
        "flat shoes"
    ]
}

# =========================
# 검색 쿼리 템플릿
# =========================

QUERY_TEMPLATES = [
    "{label} full body outfit",
    "{label} street style lookbook",
    "{label} fashion model full length",
    "{label} outfit shoes visible",
    "{label} street snap full body"
]

def build_query(label):
    template = random.choice(QUERY_TEMPLATES)
    return template.format(label=label)

# =========================
# Openverse 검색
# =========================

OPENVERSE_ENDPOINT = "https://api.openverse.org/v1/images"

def openverse_search(query: str, limit: int = 50):
    params = {"q": query, "page_size": limit}
    r = requests.get(OPENVERSE_ENDPOINT, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title"),
            "image_url": item.get("url"),
            "thumbnail": item.get("thumbnail"),
            "height": item.get("height"),
            "width": item.get("width"),
            "source": item.get("source"),
        })
    return results

# =========================
# CLIP 1차 분류 (게이팅)
# =========================

def clip_classify(image: Image.Image, category: str):
    labels = CANDIDATE_LABELS[category]

    inputs = clip_processor(
        text=labels,
        images=image,
        return_tensors="pt",
        padding=True
    )
    outputs = clip_model(**inputs)
    logits = outputs.logits_per_image[0]
    probs = logits.softmax(dim=0)

    ranked = sorted(
        [{"label": labels[i], "score": float(probs[i].item())} for i in range(len(labels))],
        key=lambda x: x["score"],
        reverse=True
    )

    is_ambiguous = False
    if len(ranked) >= 2:
        if ranked[0]["score"] - ranked[1]["score"] < 0.05:
            is_ambiguous = True

    return {
        "category": category,
        "detail_label": None if is_ambiguous else ranked[0]["label"],
        "candidates": ranked[:5],
        "is_ambiguous": is_ambiguous
    }

# =========================
# 광고 집중 필터 
# =========================

AD_SOURCES = [
    "shopify", "pinterest", "blogspot",
    "wix", "squarespace", "tumblr"
]

AD_KEYWORDS = [
    "sale", "discount", "shop", "buy",
    "store", "price", "deal"
]

def basic_filter(results):
    filtered = []
    for r in results:
        if not r.get("thumbnail"):
            continue
        if (r.get("height") or 0) < 700:
            continue
        filtered.append(r)
    return filtered

def ad_filter(results):
    filtered = []
    for r in results:
        source = (r.get("source") or "").lower()
        if any(ad in source for ad in AD_SOURCES):
            continue
        filtered.append(r)
    return filtered

def title_filter(results):
    filtered = []
    for r in results:
        title = (r.get("title") or "").lower()
        if any(k in title for k in AD_KEYWORDS):
            continue
        filtered.append(r)
    return filtered

# =========================
# CLIP 재랭킹
# =========================

def rerank_with_clip(results, target_text):
    images = []
    valid_results = []

    for r in results:
        try:
            img_bytes = requests.get(r["image_url"], timeout=5).content
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            images.append(img)
            valid_results.append(r)
        except:
            continue

    if not images:
        return []

    inputs = clip_processor(
        text=[target_text],
        images=images,
        return_tensors="pt",
        padding=True
    )

    outputs = clip_model(**inputs)
    scores = outputs.logits_per_image.softmax(dim=0).squeeze()

    ranked = sorted(
        zip(valid_results, scores.tolist()),
        key=lambda x: x[1],
        reverse=True
    )

    return [r[0] for r in ranked]

# =========================
# 최종 추천 파이프라인
# =========================

def recommend_outfit(image: Image.Image, category="outer", top_k=8):
    clip_result = clip_classify(image, category)
    label = clip_result["detail_label"] or category

    query = build_query(label)
    raw = openverse_search(query, limit=50)

    filtered = basic_filter(raw)
    filtered = ad_filter(filtered)
    filtered = title_filter(filtered)

    target_text = f"{label} full body outfit shoes visible"
    reranked = rerank_with_clip(filtered, target_text)

    final = reranked[:top_k]

    return {
        "category": clip_result["category"],
        "detailLabel": label,
        "isAmbiguous": clip_result["is_ambiguous"],
        "candidates": clip_result["candidates"],
        "queryUsed": query,
        "items": final
    }

# =========================
# API
# =========================

@app.get("/")
def read_root():
    return {"message": "FastAPI 서버 정상 실행 중"}

@app.post("/recommend/image")
async def analyze_and_search(
    image: UploadFile = File(...),
    limit: int = Form(8),
    requestId: str = Form(...)
):
    contents = await image.read()

    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except:
        return {"error": "invalid image"}

    category = "outer"  # 시스템이 카테고리 확정

    try:
        result = recommend_outfit(img, category, top_k=limit)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    return {
        "requestId": requestId,
        "result": result
    }
