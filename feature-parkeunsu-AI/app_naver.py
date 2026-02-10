"""
====================================================
AI Outfit Codynate API (CLIP + NAVER + YOLO)
----------------------------------------------------
이미지 + 텍스트 기반 패션 상품 추천 시스템

[전체 Pipeline]
1. 사용자 이미지 입력
2. CLIP 모델로 옷 카테고리 분류
3. (카테고리 + 텍스트)로 NAVER 쇼핑 검색
4. YOLO로 전신 착샷 이미지 필터링
5. CLIP으로 의미 기반 재랭킹
6. 최종 Top-K 추천 결과 반환
====================================================
"""

# =========================
# 기본 라이브러리
# =========================
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from PIL import Image
import io
import os
import requests
from io import BytesIO

# =========================
# AI 모델 관련 라이브러리
# =========================
from transformers import CLIPProcessor, CLIPModel
from ultralytics import YOLO   # YOLOv8 (사람 검출용)

# =========================
# 환경변수 로드 (.env)
# =========================
from dotenv import load_dotenv
load_dotenv()  # .env 파일을 환경변수로 로드

# =========================
# (Optional) GPT 번역 모듈
# =========================
# 한국어 텍스트를 영어로 번역해서 검색 품질을 높이기 위한 옵션
# 기본값 False → 현재는 사용하지 않음
USE_GPT_TRANSLATION = False

def gpt_translate(text: str) -> str:
    """
    GPT를 사용해 텍스트를 영어로 번역하는 코드
    (현재 프로젝트에서는 선택 사항)
    """
    if not text:
        return ""

    from openai import OpenAI
    client = OpenAI()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Translate the following text into natural English for search queries."},
            {"role": "user", "content": text}
        ]
    )
    return resp.choices[0].message.content.strip()

def translate_text(text: str) -> str:
    """
    번역 옵션 ON/OFF에 따라
    - 그대로 사용하거나
    - GPT 번역 결과 사용
    """
    if not text:
        return ""

    if USE_GPT_TRANSLATION:
        return gpt_translate(text)
    else:
        return text


# =========================
# FastAPI 앱 생성
# =========================
app = FastAPI(
    title="AI Outfit Codynate API",
    description="이미지 기반 코디 추천 서비스 (CLIP + NAVER + YOLO)",
)


# =========================
# NAVER 쇼핑 API 설정
# =========================
# .env 파일에 반드시 아래 값이 있어야 함
# NAVER_CLIENT_ID=xxxx
# NAVER_CLIENT_SECRET=yyyy

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# NAVER 쇼핑 검색 API 엔드포인트
NAVER_ENDPOINT = "https://openapi.naver.com/v1/search/shop.json"


# =========================
# CLIP 모델 로드
# =========================
# CLIP은 이미지와 텍스트의 의미적 유사도를 계산하는 모델
# - 1차: 이미지 → 옷 카테고리 분류
# - 2차: 검색 결과 이미지 재랭킹

MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)


# =========================
# YOLO 모델 로드
# =========================
# YOLOv8 nano 모델 사용
# - 빠르고 가벼움
# - 사람(person) 검출 용도

yolo_model = YOLO("yolov8n.pt")


# =========================
# 옷 카테고리 후보 라벨
# =========================
# CLIP이 이 중에서 가장 어울리는 카테고리를 선택

CANDIDATE_LABELS = [
    "jacket", "coat", "hoodie", "shirt", "t-shirt",
    "jeans", "pants", "dress", "skirt",
    "sneakers", "boots"
]
'''
초기에는 다양한 옷 종류를 반영하기 위해 카테고리 라벨을 세분화했으나,
CLIP 기반 분류에서는 라벨 수가 과도하게 많아질 경우
오히려 분류 정확도가 감소하는 현상을 확인하였다. 
“검색 쿼리 생성을 위한 상위 개념 추정”으로 재정의하고,
카테고리 라벨을 대표적인 상위 개념 위주로 축소하였다.
그 결과 전체 추천 파이프라인의 안정성과 검색 품질이 개선되었다.
'''

# =========================
# NAVER 쇼핑 검색 함수
# =========================
def naver_search(query: str, limit: int = 100):
    """
    NAVER 쇼핑 API를 사용해 상품 검색

    [입력]
    - query: 검색어
    - limit: 검색 결과 개수

    [출력]
    - 상품 정보 리스트 (이미지 URL, 제목, 링크)
    """

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    params = {
        "query": query,
        "display": limit,
        "sort": "sim"
    }

    r = requests.get(NAVER_ENDPOINT, headers=headers, params=params, timeout=10)
    r.raise_for_status()  # HTTP 에러 발생 시 예외 발생
    data = r.json()

    results = []
    for item in data["items"]:
        results.append({
            "title": item["title"],
            "image_url": item["image"],
            "link": item["link"]
        })

    return results


# =========================
# CLIP 카테고리 분류
# =========================
def clip_classify(image: Image.Image) -> str:
    """
    이미지에서 가장 어울리는 옷 카테고리 예측

    [입력]
    - image: PIL Image

    [출력]
    - CANDIDATE_LABELS 중 하나
    """

    inputs = clip_processor(
        text=CANDIDATE_LABELS,
        images=image,
        return_tensors="pt",
        padding=True
    )

    outputs = clip_model(**inputs)

    # 이미지와 각 텍스트 라벨 간 유사도 → 확률화
    probs = outputs.logits_per_image[0].softmax(dim=0)
    best_idx = probs.argmax().item()

    return CANDIDATE_LABELS[best_idx]


# =========================
# YOLO 전신 착샷 필터
# =========================
def filter_fullbody_images(results):
    """
    YOLO로 사람(person)을 검출한 뒤
    전신이 충분히 보이는 이미지(80% 이상)만 필터링

    NOTE:
    - cls == 0 → COCO 데이터셋 기준 'person'
    """

    filtered = []

    for r in results:
        try:
            # 이미지 다운로드
            img_bytes = requests.get(r["image_url"], timeout=5).content
            img = Image.open(BytesIO(img_bytes)).convert("RGB")

            yolo_results = yolo_model(img)[0]

            for box in yolo_results.boxes:
                cls = int(box.cls[0])

                # 사람(person)만 처리
                if cls == 0:
                    x1, y1, x2, y2 = box.xyxy[0]

                    # 사람 박스 높이
                    box_height = y2 - y1
                    # 전체 이미지 높이
                    img_height = img.size[1]

                    # 전신 비율 계산
                    ratio = box_height / img_height

                    # 전신 기준: 80% 이상
                    if ratio > 0.8:
                        filtered.append(r)
                        break
                    # NOTE:
                    # 전신 비율 기준을 90%로 상향할 경우
                    # 더 정확한 전신 착샷만 남길 수 있으나,
                    # 쇼핑몰 이미지 특성상 결과가 아예 없을 수 있음.
                    # 현재는 추천 안정성을 위해 80% 기준을 사용함.

        except Exception:
            # 네트워크 오류, 이미지 오류 등은 무시하고 다음으로
            continue

    return filtered


# =========================
# CLIP 재랭킹
# =========================
def rerank_with_clip(results, target_text):
    """
    CLIP을 이용해 검색 결과 이미지를
    의미적으로 더 잘 맞는 순서로 재정렬

    [입력]
    - results: 상품 리스트
    - target_text: 기준 문장
    """

    images = []
    valid_results = []

    for r in results:
        try:
            img_bytes = requests.get(r["image_url"], timeout=5).content
            img = Image.open(BytesIO(img_bytes)).convert("RGB")

            images.append(img)
            valid_results.append(r)
        except Exception:
            continue

    # 이미지가 하나도 없으면 원본 반환
    if not images:
        return results

    inputs = clip_processor(
        text=[target_text],
        images=images,
        return_tensors="pt",
        padding=True
    )

    outputs = clip_model(**inputs)

    # 이미지별 유사도 점수
    scores = outputs.logits_per_image.softmax(dim=0).squeeze()

    ranked = sorted(
        zip(valid_results, scores.tolist()),
        key=lambda x: x[1],
        reverse=True
    )

    return [r[0] for r in ranked]


# =========================
# 전체 추천 파이프라인
# =========================
def recommend_outfit(image, textQuery, top_k=8):
    """
    전체 추천 로직을 한 번에 수행하는 함수
    """

    # (1) 이미지 → 옷 카테고리 예측
    label = clip_classify(image)

    # (2) 사용자 텍스트 처리
    query_text = translate_text(textQuery)

    # (3) NAVER 쇼핑 검색
    query = f"{label} {query_text}"
    raw = naver_search(query)

    print("QUERY:", query)
    print("NAVER RAW:", len(raw))

    # (4) YOLO 전신 착샷 필터링
    raw = filter_fullbody_images(raw)
    print("AFTER YOLO:", len(raw))

    # (5) CLIP 재랭킹 기준 문장
    target_text = f"a full body photo of a person wearing {label} {query_text}"

    # (6) CLIP 재랭킹
    reranked = rerank_with_clip(raw, target_text)

    # (7) 이미지 URL 기준 중복 제거
    unique = []
    seen = set()

    for item in reranked:
        if item["image_url"] not in seen:
            seen.add(item["image_url"])
            unique.append(item)

    return unique[:top_k]


# =========================
# API 엔드포인트
# =========================
@app.post("/recommend/image")
async def analyze_and_search(
    image: UploadFile = File(...),
    limit: int = Form(8),
    requestId: str = Form(...),
    textQuery: str = Form(None)
):
    """
    이미지 업로드 기반 추천 API
    """

    contents = await image.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    try:
        items = recommend_outfit(img, textQuery, top_k=limit)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    formatted = []
    for idx, item in enumerate(items):
        formatted.append({
            "rank": idx + 1,
            "imageUrl": item["image_url"],
            "title": item["title"],
            "source": "naver"
        })

    return {
        "requestId": requestId,
        "items": formatted
    }


# =========================
# 테스트용 HTML 페이지
# =========================
@app.get("/test", response_class=HTMLResponse)
def test_page():
    return """
    <h2>AI Outfit Test (CLIP + NAVER + YOLO)</h2>
    <form action="/recommend/image" method="post" enctype="multipart/form-data">
        Image: <input type="file" name="image"><br><br>
        textQuery: <input type="text" name="textQuery" placeholder="따뜻한 겨울 남성룩"><br><br>
        <input type="hidden" name="requestId" value="test123">
        <button type="submit">SEND</button>
    </form>
    """