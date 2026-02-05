from __future__ import annotations

import io, os, time, asyncio
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image

from fastapi import Request
import traceback

import httpx
import torch
from transformers import CLIPProcessor, CLIPModel

# ================= ENV =================
from dotenv import load_dotenv
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ================= CONFIG =================
MODEL_NAME = "openai/clip-vit-base-patch32"

SEARCH_SOURCES = os.getenv("SEARCH_SOURCES", "naver,openverse").split(",")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

OPENVERSE_CLIENT_ID = os.getenv("OPENVERSE_CLIENT_ID")
OPENVERSE_CLIENT_SECRET = os.getenv("OPENVERSE_CLIENT_SECRET")

PORTRAIT_AR_MIN = 1.02
BBOX_FEET_Y_MIN = 0.86

ITEM_TOP1_MIN_PROB = 0.18
ITEM_MARGIN_MIN = 0.03

COLOR_STRICT = False

MAX_CONCURRENCY = 1 # 디버깅용
FINAL_LIMIT_DEFAULT = 8

# ================= APP =================
app = FastAPI(title="Styling Recommend API")


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    print("\n=== UNHANDLED ERROR ===")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"error": repr(exc)})

# ================= MODELS =================
device = "cuda" if torch.cuda.is_available() else "cpu"

clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# YOLO
from ultralytics import YOLO
yolo_person = YOLO("yolov8n.pt")


@torch.no_grad()
def get_img_features(img: Image.Image) -> torch.Tensor:
    inp = clip_processor(images=img, return_tensors="pt")
    pixel_values = inp["pixel_values"].to(device)

    # 1) 정석 경로
    feats = None
    try:
        feats = clip_model.get_image_features(pixel_values=pixel_values)
    except Exception as e:
        feats = None

    # 2) fallback: vision_model만 사용 (text_model 절대 타지 않음)
    if feats is None or not torch.is_tensor(feats):
        vision_out = clip_model.vision_model(pixel_values=pixel_values)
        # vision_out.pooler_output: [B, hidden]
        pooled = vision_out.pooler_output
        # CLIP은 projection을 거친 게 feature
        feats = clip_model.visual_projection(pooled)

    # 3) 안전장치
    if not torch.is_tensor(feats):
        raise TypeError(f"Image features not tensor. type={type(feats)}")

    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats



# ================= UTILS =================
def pil_rgb(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert("RGB")

def clamp(v, a, b): 
    return max(a, min(b, v))

# ================= COLOR =================
def color_compatible(user_color: str, cand_color: str) -> bool:
    u = (user_color or "").lower().strip()
    c = (cand_color or "").lower().strip()
    if not u or not c:
        return False
    if u == c:
        return True

    neutral = {"black", "white", "gray", "beige", "brown"}
    warm = {"red", "orange", "yellow", "pink", "brown", "beige"}
    cool = {"blue", "green", "purple"}

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
    w, h = img.size
    r = yolo_person.predict(img, verbose=False)[0]
    if r.boxes is None or len(r.boxes) == 0:
        return False, {}

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

    full_ok = person_h >= 0.7
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

# ================= CLIP =================
@torch.no_grad()
def clip_scores(img: Image.Image, prompts: List[str]) -> List[float]:
    inp = clip_processor(text=prompts, images=img, return_tensors="pt", padding=True)
    inp = {k: v.to(device) for k, v in inp.items()}
    out = clip_model(**inp)
    probs = out.logits_per_image.softmax(dim=1)[0]
    return probs.cpu().tolist()

# ================= NAVER IMAGE =================
async def naver_search(query: str, display=50):
    url = "https://openapi.naver.com/v1/search/image"

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, headers=headers, params=params)
        if r.status_code != 200:
            print("[NAVER ERR]", r.status_code, r.text[:200])
            return []
        return r.json().get("items", [])

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
    print("요청 들어옴", requestId, textQuery)

    if not NAVER_CLIENT_ID:
        return {"error": "NAVER_CLIENT_ID 없음"}

    if not NAVER_CLIENT_SECRET:
        return {"error": "NAVER_CLIENT_SECRET 없음"}

    user_img = pil_rgb(await image.read())
    user_q = (textQuery or "").strip()
    if user_q:
        style_part = f"{user_q} 코디 전신"
    else:
        style_part = "코디 전신 스트릿룩 데일리룩"

    # [1] 상수 및 프롬프트 정의 (함수 시작할 때 미리 선언)
    DEFAULT_PROMPTS = [
    "a photo of casual clothing",
    "a photo of street fashion outfit",
    "a photo of a fashion item",
    ]

    SUBTYPE_PROMPTS = {
    "footwear": [
        "a photo of sneakers",
        "a photo of loafers",
        "a photo of derby shoes",
        "a photo of boots",
        "a photo of sandals",
    ],
    "top": [
        "a photo of a white t-shirt",
        "a photo of a black t-shirt",
        "a photo of a shirt",
        "a photo of a hoodie",
        "a photo of a knit sweater",
    ],
    "bottom": [
        "a photo of jeans",
        "a photo of slacks",
        "a photo of shorts",
        "a photo of a skirt",
    ],
    "outerwear": [
        "a photo of a coat",
        "a photo of a blazer",
        "a photo of a jacket",
        "a photo of a padded jacket",
    ],
    "accessory": [
        "a photo of a bag",
        "a photo of a cap",
        "a photo of a belt",
        "a photo of sunglasses",
    ],
    }

    CATEGORY_LABELS = {
        "footwear": "a photo of footwear (shoes, sneakers, boots)",
        "top": "a photo of a top (t-shirt, shirt, hoodie, sweater)",
        "bottom": "a photo of bottoms (jeans, slacks, skirt, shorts)",
        "outerwear": "a photo of outerwear (coat, jacket, blazer)",
        "accessory": "a photo of an accessory (bag, cap, belt)",
    }

    # 1. 매핑 테이블 정의 

    cat_kor_map = {
        "footwear": "신발",
        "top": "상의",
        "bottom": "하의",
        "outerwear": "아우터",
        "accessory": "악세사리",
    }

    # 2 baseLabel(영어) -> 최소한의 한국어 힌트(간단 매핑, 없으면 base 그대로)
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

    # prompt가 2세트라서 인덱스를 색상으로 다시 묶어야 함
    # (각 색상이 2개 prompt를 가짐)
    by_color = []
    for i in range(len(COLOR_LABELS)):
        by_color.append(max(color_scores[i], color_scores[i+len(COLOR_LABELS)]))

    detected_color = COLOR_LABELS[int(torch.tensor(by_color).argmax())]

    color_kor = color_kor_map.get(detected_color, "")

# ====================================================================

    # 3. 카테고리 및 Subtype 추론

    # [3] 카테고리 추론 (best_idx 사용)
    category_prompts = list(CATEGORY_LABELS.values())
    cat_scores = clip_scores(user_img, category_prompts)
    best_idx = int(torch.tensor(cat_scores).argmax())
    cat_key = list(CATEGORY_LABELS.keys())[best_idx]
    cat_kor = cat_kor_map.get(cat_key, "패션")

    # [4] Subtype 추론 (top_idx, baseLabel 사용)
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

    # [6] 검색 쿼리 생성 (모든 정보가 취합된 후 실행)
    # 예: "베이지 숏 코트 전신 코디 룩북"
    korean_query = f"{color_kor} {cat_kor} {base_kor} {user_q} 전신 코디 착샷 룩북 스타일링".strip()

    naver_items = await naver_search(korean_query, display=100)
    if len(naver_items) < 20: # 결과가 너무 적으면 쿼리 완화
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

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    
# ====================================================================

    # [7]. 시각적 유사도용 특징 추출 (process 밖에서 한 번만)
    user_features = get_img_features(user_img)

# ====================================================================

    # [8]. 개별 이미지 처리 (process)
    async with httpx.AsyncClient(timeout=15) as client:

        async def process(it):
            async with sem:
                try:
                    # 1) 이미지 다운로드
                    r = await client.get(it["link"])
                    if r.status_code != 200:
                            return None
                    # 이미지 변환 예외 처리 추가
                    try:
                        img = pil_rgb(r.content)
                    except:
                        return None

                    # 2) 전신 + 발끝 필터
                    ok, bbox = bbox_fullbody_and_feet(img)
                    if not ok:
                        return None
                    
                    # 3) 시각적 유사도 계산 (추가된 핵심 로직)
                    cand_features = get_img_features(img)
                    
                    # 코사인 유사도 계산 (사용자 이미지 vs 검색된 코디 이미지)
                    # 이 점수가 높을수록 사용자가 올린 아이템과 색상/재질이 비슷한 코디입니다.
                    visual_sim = (user_features @ cand_features.T).item()

                    # 4) 세로형 비율 점수
                    ar = img.height / img.width
                    ar_score = ar if ar >= PORTRAIT_AR_MIN else 0.9

                    # 5) CLIP 아이템 일치 점수
                    match_scores = clip_scores(img, subtype_prompts)
                    item_score = max(match_scores)

                    # 6) textQuery 스타일 점수 추가
                    style_score = 0.0

                    if user_q:
                        style_prompts = [
                            f"a full body {user_q} outfit photo",
                            f"a {user_q} street fashion lookbook",
                            f"a fashion style of {user_q}",
                        ]
                        style_scores = clip_scores(img, style_prompts)
                        style_score = max(style_scores)

                    # margin = top1 - second best
                    sorted_scores = sorted(match_scores, reverse=True)
                    margin = sorted_scores[0] - sorted_scores[1]

                    # 7) 스코어 계산 가중치 조정
                    # visual_sim(시각적 유사도)에 높은 비중을 둡니다.
                    score = (
                        0.40 * visual_sim +      # 사용자가 올린 '그 아이템'과 얼마나 닮았나 (색상, 재질)
                        0.25 * item_score +      # 텍스트 카테고리(예: '코트')와 일치하나
                        0.15 * style_score +
                        0.10 * ar_score +        # 세로 사진인가
                        0.10 * bbox["person_h"]  # 사람이 크게 찍혔나
                    )

                    # 8) 패널티 로직 (기존 유지하되 수치 조정 가능)
                    penalty = 0.0
                    # 아이템 확신이 너무 낮으면 패널티
                    if item_score < ITEM_TOP1_MIN_PROB:
                        penalty += 0.12

                    # 1등-2등 차이가 작으면 패널티 (애매한 분류)
                    if margin < ITEM_MARGIN_MIN:
                        penalty += 0.10

                    # 스타일 반영했는데도 점수가 낮으면 추가 패널티
                    if user_q and style_score < 0.12:
                        penalty += 0.05

                    # 사용자가 올린 아이템과 너무 안 닮으면 패널티
                    if visual_sim < 0.35:
                        penalty += 0.10    

                    score -= penalty

                    thumb = it.get("thumbnail") or it.get("link")
                    title = (it.get("title") or "").replace("<b>", "").replace("</b>", "")

                    return {
                        "imageUrl": it["link"],
                        "title": title,
                        "source": "naver",
                        "score": clamp(score, 0, 2),
                    }
                
                except Exception as e:
                    print("process error:", e)
                    return None


        processed = await asyncio.gather(*[process(it) for it in naver_items])

    # [9]. 결과 정렬 및 반환 (client 블록 밖에서 수행 가능)
    items = [x for x in processed if x]
    items.sort(key=lambda x: x["score"], reverse=True)

    top_items = items[:limit]
    for idx, it in enumerate(top_items, start=1):
        it["rank"] = idx

    # [9]. 최종 반환 (with 블록 밖으로 나옴)
    return {
        "requestId": requestId,
        "items": top_items,
        # "query": korean_query,
        # "category": category.replace("a photo of ", ""),
        # "baseLabel": baseLabel,
        # "targetPrompt": target_prompt,
        # "rawCount": len(naver_items),
        # "itemsCount": len(top_items),
    }
           

# python -m uvicorn main:app --reload
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug

