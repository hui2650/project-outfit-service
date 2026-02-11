from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io, os, asyncio, traceback

import torch
import httpx
from transformers import CLIPProcessor, CLIPModel
from ultralytics import YOLO
from dotenv import load_dotenv

# =====================================================
# ENV
# =====================================================
load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

print("=== ENV CHECK ===")
print("NAVER_CLIENT_ID:", NAVER_CLIENT_ID)
print("NAVER_CLIENT_SECRET:", "SET" if NAVER_CLIENT_SECRET else None)
print("=================")

MODEL_NAME = "openai/clip-vit-base-patch32"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

FINAL_LIMIT = 8
MAX_CONCURRENCY = 4

# =====================================================
# APP
# =====================================================
app = FastAPI(title="Unified Outfit Recommendation API")

# =====================================================
# MODELS
# =====================================================
print("Loading CLIP model...")
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE).eval()
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

print("Loading YOLO model...")
yolo = YOLO("yolov8n.pt")

# =====================================================
# UTILS
# =====================================================
def pil_rgb(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert("RGB")


@torch.no_grad()
def image_embedding(img: Image.Image) -> torch.Tensor:
    print("🔥 image_embedding called")

    inp = clip_processor(images=img, return_tensors="pt")
    pixel_values = inp["pixel_values"].to(DEVICE)

    vision_out = clip_model.vision_model(pixel_values=pixel_values)
    pooled = vision_out.pooler_output
    feats = clip_model.visual_projection(pooled)

    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


def is_fullbody(img: Image.Image) -> bool:
    try:
        h = img.height
        r = yolo.predict(img, verbose=False)[0]

        if r.boxes is None:
            print("YOLO: no boxes")
            return False

        boxes = r.boxes.xyxy.cpu().numpy()
        cls = r.boxes.cls.cpu().numpy()

        persons = [i for i, c in enumerate(cls) if int(c) == 0]
        if not persons:
            print("YOLO: no person detected")
            return False

        i = max(persons, key=lambda i: boxes[i][3] - boxes[i][1])
        x1, y1, x2, y2 = boxes[i]

        person_ratio = (y2 - y1) / h
        head_ok = (y1 / h) <= 0.15
        feet_ok = (y2 / h) >= 0.85

        ok = person_ratio >= 0.7 and head_ok and feet_ok
        print(f"YOLO fullbody={ok}, ratio={person_ratio:.2f}")

        return ok

    except Exception as e:
        print("YOLO ERROR:", e)
        traceback.print_exc()
        return False


async def naver_image_search(query: str, limit=80):
    print(">>> NAVER SEARCH QUERY:", query)

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("❌ NAVER API KEY MISSING")
        return []

    url = "https://openapi.naver.com/v1/search/image"

    # ✅ 정상적인 headers 딕셔너리
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    params = {
        "query": query,
        "display": limit
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=headers, params=params)
        print("NAVER STATUS:", r.status_code)

        if r.status_code != 200:
            print("NAVER RESPONSE:", r.text[:200])
            return []

        items = r.json().get("items", [])
        print("NAVER ITEMS COUNT:", len(items))
        return items

# =====================================================
# MAIN API
# =====================================================
@app.post("/recommend/image")
async def recommend_image(
    image: UploadFile = File(...),
    requestId: str = Form(...),
    textQuery: str = Form("")
):
    print("\n=== REQUEST START ===")
    print("requestId:", requestId)
    print("textQuery:", textQuery)
    print("filename:", image.filename)

    try:
        user_img = pil_rgb(await image.read())
        print("User image loaded")

        user_vec = image_embedding(user_img)
        print("User embedding OK")

        query = f"{textQuery} 전신 코디 룩북" if textQuery else "전신 코디 스트릿룩"
        raw_items = await naver_image_search(query)

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async with httpx.AsyncClient(timeout=15) as client:

            async def process(it):
                async with sem:
                    try:
                        img_url = it.get("thumbnail") or it.get("link")
                        if not img_url:
                            print("NO IMAGE URL")
                            return None

                        r = await client.get(img_url)
                        if r.status_code != 200:
                            print("IMAGE DOWNLOAD FAIL:", img_url)
                            return None

                        ct = r.headers.get("content-type", "")
                        if not ct.startswith("image/"):
                            print("NOT IMAGE:", ct, img_url)
                            return None

                        img = pil_rgb(r.content)

                        if not is_fullbody(img):
                            return None

                        cand_vec = image_embedding(img)
                        visual_sim = (user_vec @ cand_vec.T).item()

                        ar = img.height / img.width
                        ar_score = min(ar / 1.3, 1.0)

                        score = 0.9 * visual_sim + 0.1 * ar_score

                        return {
                            "imageUrl": img_url,
                            "title": (it.get("title") or "")
                                        .replace("<b>", "")
                                        .replace("</b>", ""),
                            "score": score,
                        }

                    except Exception as e:
                        print("PROCESS ERROR:", e)
                        traceback.print_exc()
                        return None

            processed = await asyncio.gather(*[process(it) for it in raw_items])

        items = [x for x in processed if x]
        print("FINAL ITEMS:", len(items))

        items.sort(key=lambda x: x["score"], reverse=True)
        final = items[:FINAL_LIMIT]

        for i, it in enumerate(final, start=1):
            it["rank"] = i
            it["source"] = "naver"

        print("=== REQUEST END ===\n")

        return {
            "requestId": requestId,
            "items": final
        }

    except Exception as e:
        print("🔥 FATAL ERROR IN recommend_image")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )