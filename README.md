# Outfit Service — Hybrid AI Outfit Recommendation Service
#### YOLO · CLIP 기반 이미지 분석을 활용한 AI 코디 추천 서비스
#### 이미지 분석과 스타일 유사도 모델을 활용하여 코디 추천 과정을 자동화한 AI 기반 웹 서비스입니다.

---

## Built With (핵심 기술)
![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)
![Spring Boot](https://img.shields.io/badge/SpringBoot-6DB33F?style=flat&logo=springboot&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-AI-orange?style=flat)
![CLIP](https://img.shields.io/badge/CLIP-OpenAI-blue?style=flat)
![Deploy](https://img.shields.io/badge/Deploy-Vercel%20%7C%20Render-black?style=flat)

---

## 소개

#### 이미지와 스타일 정보를 기반으로 코디를 추천해주는 AI 웹 서비스입니다.  
#### 기존 패션 이미지 검색은 상품 중심 결과가 많아 실제 착장 스타일을 파악하기 어렵다는 한계가 있습니다.
#### 본 프로젝트는 YOLO 기반 사람 검출과 CLIP 임베딩 유사도 분석을 활용하여 스타일을 분석하고,  
#### 이미지 검색 API를 통해 다양한 코디 결과를 제공합니다.

---

## 프로젝트 목표

#### - 기존 이미지 검색 기반 코디 추천 서비스는
#### - "상품 중심" 결과가 많고, 실제 착용 코디 이미지 추천이 어렵다는 한계를 가집니다.

#### - 본 프로젝트는 YOLO 기반 사람 검출 + CLIP 유사도 분석을 결합하여
#### - 실제 착용 코디 이미지 중심의 추천 시스템을 구현하는 것을 목표로 합니다.

---

## 기술 스택

### Frontend
#### React · Vite · Tailwind CSS  

### Backend
#### Spring Boot  

### AI Server
#### FastAPI · YOLOv8 · CLIP · Transformers · Torch  

---

## 아키텍처 다이어그램

![Uploading image.png…]()

---

## 🤖 AI Pipeline

1. YOLOv8 Person Detection
2. Outfit Region Crop
3. CLIP Embedding Extraction
4. Image Search API 호출
5. CLIP 유사도 재랭킹
6. 색상 거리 기반 보정
7. 결과 반환

---

## 주요 기능

#### - 이미지 업로드 기반 코디 추천  
#### - YOLOv8 기반 사람 및 아이템 탐지  
#### - CLIP 모델을 활용한 스타일 유사도 분석  
#### - 네이버 / 카카오 이미지 검색 API 연동  
#### - Follow-up Chat 기능  
#### - Dark / Light 모드 지원  

---

## Technical Challenges

### 1. Frontend-Backend-AI 서버 비동기 처리 문제
- 중복 요청 발생
- 무한 로딩 이슈
→ submitLock + turn 기반 상태 관리로 해결

### 2. 이미지 검색 결과가 상품 이미지로만 나오는 문제
→ YOLO Person Gate + Negative Prompt 강화

### 3. CLIP 유사도만으로는 색상 정확도가 낮은 문제
→ Dominant RGB 추출 + 색상 거리 점수 반영

### 4. 강한 필터링으로 후보 부족 발생
→ 단계적 필터 완화 전략 적용

---

## 프로젝트 구조

#### project-outfit-service
#### ├ outfit-front
#### ├ outfit-back
#### └ outfit-py

---

## API Example

POST /api/v1/recommend/image

Request
- image: multipart file
- category: string
- gender: string
- textQuery: string

Response
{
  "requestId": "req_1234",
  "items": [
    {
      "imageUrl": "...",
      "similarity": 0.82,
      "colorScore": 0.91
    }
  ]
}

---

## Screenshots
<img width="1369" height="942" alt="bg-hero-1" src="https://github.com/user-attachments/assets/d4da9426-cd1d-400c-9ab7-1df86e98a11e" />
<img width="1337" height="938" alt="panel" src="https://github.com/user-attachments/assets/b6c7649a-89aa-43c2-b009-df4fa944246d" />

---

## 실행 방법
#### 터미널(cmd 또는 VSCode Terminal)을 열고 아래 명령어를 순서대로 실행합니다.

### ▶ Frontend
* cd outfit-front
* ↓ 
* npm install
* ↓ 
* npm run dev

### ▶ Backend
* cd outfit-back
* ↓ 
* gradlew bootRun

### ▶ AI Server
* cd outfit-py
* ↓ 
* pip install -r requirements.txt
* ↓ 
* uvicorn main:app --reload

---

## 환경 변수 (.env)

* OPENAI_API_KEY = your_openai_api_key
* NAVER_CLIENT_ID = your_naver_client_id
* NAVER_CLIENT_SECRET = your_naver_client_secret
* KAKAO_REST_API_KEY = your_kakao_rest_api_key


---

