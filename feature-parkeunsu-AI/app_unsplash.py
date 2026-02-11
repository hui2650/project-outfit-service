from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from PIL import Image
import io
import requests
from transformers import CLIPProcessor, CLIPModel
from io import BytesIO
from enum import Enum
import unicodedata

app = FastAPI(
    title="AI Outfit Codynate API",
    description="이미지 기반 코디 추천 서비스",
)

# 서버 실행:
# uvicorn "app(test):app" --reload

# =========================
# Enum (선택형 UI용)
# =========================

class GenderEnum(str, Enum):
    male = "male"
    female = "female"

class AgeEnum(str, Enum):
    teen = "teen"
    s20 = "20s"
    s30 = "30s"
    s40 = "40s"

class SeasonEnum(str, Enum):
    spring = "spring"
    summer = "summer"
    fall = "fall"
    winter = "winter"

class MoodEnum(str, Enum):
    casual = "casual"
    minimal = "minimal"
    street = "street"
    formal = "formal"
    sporty = "sporty"

# =========================
# Unsplash 설정
# =========================

UNSPLASH_ACCESS_KEY = "pwZYYRV0x4ju6H2fkvdiqd2GNz1Ic8T5c-Q0ouQ2PXw"
UNSPLASH_ENDPOINT = "https://api.unsplash.com/search/photos"

# =========================
# CLIP 모델
# =========================

MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# =========================
# 라벨
# =========================

CANDIDATE_LABELS = {
    "outer": [
        "a photo of a beige trench coat",
        "a photo of a long coat",
        "a photo of a wool coat",
        "a photo of a padded jacket",
        "a photo of a leather jacket",
        "a photo of a denim jacket",
        "a photo of a blazer",
        "a photo of a cardigan",
        "a photo of a parka",
        "a photo of a field jacket",
        "a photo of a windbreaker",
        "a photo of a bomber jacket",
        "a photo of a fleece jacket"
    ],

    "top": [
        "a photo of a t-shirt",
        "a photo of a long sleeve t-shirt",
        "a photo of a hoodie",
        "a photo of a sweatshirt",
        "a photo of a knit sweater",
        "a photo of a shirt",
        "a photo of a blouse",
        "a photo of a polo shirt",
        "a photo of a sleeveless top",
        "a photo of a crop top"
    ],

    "bottom": [
        "a photo of jeans",
        "a photo of slacks",
        "a photo of sweatpants",
        "a photo of shorts",
        "a photo of skirt",
        "a photo of mini skirt",
        "a photo of long skirt",
        "a photo of wide pants",
        "a photo of skinny jeans",
        "a photo of cargo pants"
    ],

    "onepiece": [
        "a photo of a dress",
        "a photo of a long dress",
        "a photo of a mini dress",
        "a photo of a shirt dress",
        "a photo of a knit dress",
        "a photo of a denim dress",
        "a photo of a formal dress"
    ],

    "shoes": [
        "a photo of sneakers",
        "a photo of running shoes",
        "a photo of loafers",
        "a photo of boots",
        "a photo of ankle boots",
        "a photo of sandals",
        "a photo of slippers",
        "a photo of heels",
        "a photo of flat shoes"
    ],

    "bag": [
        "a photo of a backpack",
        "a photo of a tote bag",
        "a photo of a shoulder bag",
        "a photo of a crossbody bag",
        "a photo of a clutch bag",
        "a photo of a messenger bag"
    ]
}

# =========================
# 한글 → ASCII 강제 정규화
# =========================

def to_ascii_safe(text: str):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

# =========================
# Unsplash
# =========================

def unsplash_search(query: str, limit: int = 50):
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }
    params = {
        "query": query,
        "per_page": limit,
        "orientation": "portrait"
    }

    r = requests.get(UNSPLASH_ENDPOINT, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data["results"]:
        results.append({
            "title": item["description"] or item["alt_description"],
            "image_url": item["urls"]["regular"],
            "thumbnail": item["urls"]["small"],
        })
    return results

# =========================
# CLIP 분류
# =========================

def clip_classify(image: Image.Image):
    labels = CANDIDATE_LABELS["outer"]

    inputs = clip_processor(
        text=labels,
        images=image,
        return_tensors="pt",
        padding=True
    )

    outputs = clip_model(**inputs)
    probs = outputs.logits_per_image[0].softmax(dim=0)

    ranked = sorted(
        [{"label": labels[i], "score": float(probs[i].item())}
         for i in range(len(labels))],
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked[0]["label"]

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
# 추천 파이프라인
# =========================

def recommend_outfit(image, userText, gender, age, season, mood, top_k=8):
    label = clip_classify(image)

    # 한글 → ASCII 강제 변환
    safe_text = to_ascii_safe(userText)

    query = f"{gender} {age} {season} {mood} {label} {safe_text} full body outfit"
    raw = unsplash_search(query)

    target_text = f"a {age} {gender} wearing {label} {mood} {season} fashion"
    reranked = rerank_with_clip(raw, target_text)

    return {
        "queryUsed": query,
        "items": reranked[:top_k]
    }

# =========================
# API
# =========================

@app.post("/recommend/image")
async def analyze_and_search(
    image: UploadFile = File(...),
    limit: int = Form(8),
    requestId: str = Form(...),
    userText: str = Form(""),
    gender: GenderEnum = Form(GenderEnum.male),
    ageGroup: AgeEnum = Form(AgeEnum.s20),
    season: SeasonEnum = Form(SeasonEnum.fall),
    mood: MoodEnum = Form(MoodEnum.casual)
):
    contents = await image.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    try:
        result = recommend_outfit(
            img,
            userText,
            gender.value,
            ageGroup.value,
            season.value,
            mood.value,
            top_k=limit
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {
        "requestId": requestId,
        "result": result
    }

# =========================
# UTF-8 안전 테스트 페이지
# =========================

@app.get("/test", response_class=HTMLResponse)
def test_page():
    return """
    <h2>AI Outfit Test (UTF-8 SAFE)</h2>
    <form action="/recommend/image" method="post" enctype="multipart/form-data">
        Image: <input type="file" name="image"><br><br>
        userText: <input type="text" name="userText" placeholder="시원한 여름 데이트룩"><br><br>

        Gender:
        <select name="gender">
            <option value="male">male</option>
            <option value="female">female</option>
        </select><br><br>

        Age:
        <select name="ageGroup">
            <option value="teen">teen</option>
            <option value="20s">20s</option>
            <option value="30s">30s</option>
            <option value="40s">40s</option>
        </select><br><br>

        Season:
        <select name="season">
            <option value="spring">spring</option>
            <option value="summer">summer</option>
            <option value="fall">fall</option>
            <option value="winter">winter</option>
        </select><br><br>

        Mood:
        <select name="mood">
            <option value="casual">casual</option>
            <option value="minimal">minimal</option>
            <option value="street">street</option>
            <option value="formal">formal</option>
            <option value="sporty">sporty</option>
        </select><br><br>

        <input type="hidden" name="requestId" value="test123">
        <input type="hidden" name="limit" value="8">

        <button type="submit">SEND</button>
    </form>
    """
