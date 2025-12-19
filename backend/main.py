from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

from routers import auth, langgraph_chat  # LangGraph 라우터 추가
from core.database import engine, Base  # 1. engine과 Base 가져오기

# 2. 서버 시작 때 테이블 생성 (없으면 만들고, 있으면 넘어감)
# DB 서버가 없어도 서버는 시작되도록 try-except 처리
try:
    Base.metadata.create_all(bind=engine)
    print("✅ DB 테이블 생성 완료")
except Exception as e:
    print(f"⚠️ DB 연결 실패 (DB 없이 실행): {e}")
    print("   ℹ️ 인증 기능은 사용 불가하지만 LangGraph 챗봇은 정상 작동합니다.")

# 앱 초기화
app = FastAPI(
    title="AIX Random Travel Platform",
    description="AI 기반 랜덤 즉흥 여행 엔터테인먼트 플랫폼 API",
    version="1.1"
)

# CORS 설정 (리액트 연동용)
# 리액트 기본 포트인 3000번을 허용해줍니다.
origins = [
    "http://localhost:3000",
    "http://localhost:3001",  # Vite 자동 포트 변경
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",  # Vite 자동 포트 변경
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://192.168.0.222:3000",
    "http://192.168.0.222:5000",
    "http://192.168.0.222:5173",
    "http://192.168.0.222:5174",
    "http://192.168.0.222:8000",
    "http://192.168.0.222:8001",
    "http://192.168.0.222:8002",
    "http://192.168.0.222:8003",
    "http://192.168.0.222:8004",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 라우터 예시 (나중에 파일 분리 시 routers 폴더로 이동) ---
@app.get("/")
def read_root():
    return {"message": "AIX Travel Platform API Server Running!"}

# 문서에 명시된 기본 헬스 체크용
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "version": "1.1"}

# 라우터 등록
app.include_router(auth.router)
app.include_router(langgraph_chat.router)  # LangGraph 멀티에이전트 라우터 등록




# --- 여기에 추후 도메인별 라우터를 include 하게 됩니다 ---
# from app.routers import auth, trips, agents
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
# app.include_router(trips.router, prefix="/api/v1/trips", tags=["Trips"])