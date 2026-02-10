import os
import io
import asyncio
import traceback
from pathlib import Path

import torch
import torch.nn.functional as F
import httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from ultralytics import YOLO
from dotenv import load_dotenv

# =====================================================
# [흐름 1] 시스템 환경 및 AI 모델 초기화
# 프로그램 시작 시, 필요한 API 키를 로드하고 AI의 뇌(CLIP, YOLO)를 메모리에 올립니다.
# =====================================================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").replace('"', '').strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").replace('"', '').strip()

MODEL_NAME = "openai/clip-vit-base-patch32"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="AI Fashion Lookbook Engine")

print(f"🚀 고성능 스타일링 엔진 기동 중... (Device: {DEVICE})")
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)
yolo = YOLO("yolov8n.pt") 

# [데이터 흐름의 기준점] AI가 비교 분석할 대상 카테고리 정의
CLOTHING_CATEGORIES = [
    "puffer padding jacket", "long wool coat", "casual hoodie", 
    "oversized sweatshirt", "mini skirt", "long maxi skirt", 
    "denim jeans", "wide slacks", "formal blazer", "training pants"
]
GENDER_LABELS = ["a photo of a man's fashion", "a photo of a woman's fashion"]
COLOR_LABELS = ["black", "white", "grey", "beige", "navy", "red", "blue", "green", "pink", "yellow"]
COLOR_MAP_KO = {
    "black": "검정색", "white": "흰색", "grey": "회색", "beige": "베이지색", 
    "navy": "네이비", "red": "빨간색", "blue": "파란색", "green": "초록색", 
    "pink": "분홍색", "yellow": "노란색"
}

# =====================================================
# [흐름 2] 데이터 변환 유틸리티
# 이미지나 텍스트를 AI가 계산할 수 있는 '수학적 벡터'로 변환하는 통로입니다.
# =====================================================

@torch.no_grad()
def get_features(img=None, text=None):
    """입력 데이터를 벡터 좌표로 변환하여 '유사도 비교'가 가능하게 만듭니다."""
    if img:
        inputs = clip_processor(images=img, return_tensors="pt").to(DEVICE)
        outputs = clip_model.get_image_features(**inputs)
    else:
        inputs = clip_processor(text=text if isinstance(text, list) else [text], 
                                return_tensors="pt", padding=True).to(DEVICE)
        outputs = clip_model.get_text_features(**inputs)
    return F.normalize(outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs, p=2, dim=-1)

def is_real_coordi(img: Image.Image) -> bool:
    """YOLO 모델을 통해 '사람' 객체가 있는지 확인하여 가짜(상품샷)를 걸러냅니다."""
    results = yolo.predict(img, verbose=False, conf=0.25)
    return any(int(c) == 0 for r in results for c in r.boxes.cls)

# =====================================================
# [흐름 3] 메인 프로세스: 스타일링 추천 엔진
# 사용자의 입력을 받아 최종 추천 리스트를 생성하는 핵심 워크플로우입니다.
# =====================================================

@app.post("/recommend-outfit")
async def recommend(
    image: UploadFile = File(...), 
    style_keyword: str = Form("트렌디한")
):
    try:
        # -----------------------------------------------------
        # STEP 1: 입력 데이터 디지털화 (Feature Extraction)
        # 사용자가 올린 이미지를 읽고 AI가 이해하는 특징 벡터(user_vec)로 변환합니다.
        # -----------------------------------------------------
        user_img_bytes = await image.read()
        user_img = Image.open(io.BytesIO(user_img_bytes)).convert("RGB")
        user_vec = get_features(img=user_img)
        style_vec = get_features(text=style_keyword)

        # -----------------------------------------------------
        # STEP 2: 다각도 이미지 분석 (Classification)
        # 사용자 사진을 '성별', '아이템', '색상' 세 가지 관점에서 분류합니다.
        # -----------------------------------------------------
        # 2-1. 성별 분석: 남성/여성 벡터와 비교하여 결정
        gender_feats = get_features(text=GENDER_LABELS)
        gender_idx = (user_vec @ gender_feats.T).argmax().item()
        gender_str = "여성" if gender_idx == 1 else "남성"

        # 2-2. 아이템 분석: 사전에 정의된 10종의 의류 카테고리와 비교
        item_feats = get_features(text=CLOTHING_CATEGORIES)
        item_idx = (user_vec @ item_feats.T).argmax().item()
        detected_item = CLOTHING_CATEGORIES[item_idx]

        # 2-3. 색상 분석: 색상 레이블과 비교하여 가장 유사한 색상 추출
        color_text_labels = [f"a photo of {c} color clothing" for c in COLOR_LABELS]
        color_feats = get_features(text=color_text_labels)
        color_idx = (user_vec @ color_feats.T).argmax().item()
        detected_color_en = COLOR_LABELS[color_idx]
        detected_color_ko = COLOR_MAP_KO.get(detected_color_en, "")

        # -----------------------------------------------------
        # STEP 3: 외부 데이터 탐색 (Search)
        # 분석된 특징(성별+색상+아이템)을 조합해 네이버 이미지 검색 API로 룩북을 찾습니다.
        # -----------------------------------------------------
        search_query = f"{gender_str} {detected_color_ko} {detected_item} {style_keyword} 스타일링 룩북 ootd"
        print(f"💎 데이터 흐름: 분석 완료 -> 검색 쿼리 생성: {search_query}")

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            n_resp = await client.get(
                "https://openapi.naver.com/v1/search/image",
                headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET},
                params={"query": search_query, "display": 50, "sort": "sim"}
            )
            
            items = n_resp.json().get("items", [])
            final_candidates = []
            
            # -----------------------------------------------------
            # STEP 4: 정밀 필터링 및 점수화 (Re-ranking)
            # 검색된 사진들이 진짜 '사람이 입은 코디'인지 확인하고 유사도를 계산합니다.
            # -----------------------------------------------------
            for item in items[:40]:
                try:
                    url = item["link"]
                    r = await client.get(url, timeout=2.5)
                    if r.status_code != 200: continue
                    t_img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    
                    # 흐름 제어: 사람이 없는 사진은 후보군에서 즉시 탈락
                    if not is_real_coordi(t_img): continue 
                    
                    t_vec = get_features(img=t_img)
                    
                    # 점수 합산 흐름: (원본과의 시각적 유사성 30%) + (스타일 키워드 부합도 70%)
                    v_score = (user_vec @ t_vec.T).item()
                    s_score = (style_vec @ t_vec.T).item()
                    total_score = (v_score * 0.3) + (s_score * 0.7)
                    
                    final_candidates.append({"url": url, "score": total_score})
                except: continue

        # -----------------------------------------------------
        # STEP 5: 최종 데이터 정렬 및 응답 (Output)
        # 가장 높은 점수를 받은 스타일링 사진 8개를 선별하여 사용자에게 반환합니다.
        # -----------------------------------------------------
        final_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "status": "success",
            "message": f"AI가 분석한 '{gender_str}' 고객님의 '{detected_color_ko} {detected_item}' 스타일링 제안입니다.",
            "analysis": {
                "detected_gender": gender_str,
                "detected_item": detected_item,
                "detected_color": detected_color_ko,
                "applied_style": style_keyword
            },
            "lookbook_results": [c["url"] for c in final_candidates[:8]]
        }

    except Exception as e:
        # 에러 발생 시의 흐름: 트래킹 로그를 남기고 사용자에게 에러 메시지 전송
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    # 서버 기동 흐름: 0.0.0.0 주소의 8000번 포트에서 API 서비스 시작
    uvicorn.run(app, host="0.0.0.0", port=8000)