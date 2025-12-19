# Localy Travel Platform - 설정 가이드

## 🚀 빠른 시작

### 1. 백엔드 실행

```bash
cd localy-main/backend

# 가상환경 활성화 (Windows)
.\venv\Scripts\activate

# 의존성 설치 (최초 1회)
pip install -r requirements.txt

# 서버 실행
python -m uvicorn main:app --reload --port 8000
```

**백엔드 URL**: http://localhost:8000
**API 문서**: http://localhost:8000/docs

### 2. 프론트엔드 실행

```bash
cd localy-main

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

**프론트엔드 URL**: http://localhost:3000

---

## 📝 주요 설정

### 환경 변수 (`.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 데이터베이스 연결

파일: `backend/core/database.py`

```python
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://travel:travel12!!@192.168.0.222:3306/travel_platform"
```

### AI 모델 서버 (캠프 vLLM)

파일: `backend/routers/ai.py`

```python
KKACHIL_SERVER = "https://ccqrh-125-6-60-4.a.free.pinggy.link/v1"  # pinggy 터널
```

**모델 이름**: `/home/kampuser/notebooks/models/kkachil-cat-merged`

---

## 🤖 AI 챗봇 기능

### 플로팅 챗봇 버튼
- **위치**: 모든 페이지 우측 하단
- **기능**: 클릭하면 까칠이 AI와 실시간 대화
- **API**: `/api/chat/kkachil`

### 회원가입 페르소나 수집 
- **컴포넌트**: `ChatScreen.tsx`
- **기능**: 회원가입 시 AI가 사용자 선호도 수집
- **저장**: DB + 로컬스토리지

---

## 🛠️ API 엔드포인트

### 백엔드 (http://localhost:8000)

#### 인증
- `POST /auth/signup` - 회원가입
- `POST /auth/login` - 로그인
- `PUT /auth/update-profile` - 프로필 업데이트

#### AI 챗봇
- `POST /api/chat/kkachil` - 까칠이 AI 대화
- `POST /api/chat/sundong` - 순둥이 AI 대화
- `GET /api/chat/health` - AI 서비스 상태 확인

#### 시스템
- `GET /api/v1/health` - 백엔드 헬스 체크

---

## 📦 주요 컴포넌트

### 백엔드
- `main.py` - FastAPI 앱 엔트리포인트
- `routers/auth.py` - 인증 라우터
- `routers/ai.py` - AI 챗봇 라우터
- `models.py` - DB 모델 (User, Persona, File, Board)
- `core/database.py` - DB 연결 설정

### 프론트엔드
- `App.tsx` - 메인 앱 + 플로팅 챗봇
- `FloatingChatBot.tsx` - 플로팅 챗봇 UI
- `ChatScreen.tsx` - 회원가입 페르소나 챗봇
- `TravelChatBot.tsx` - 여행 계획 챗봇
- `aiApi.ts` - AI API 통신 유틸리티

---

## 🔑 핵심 기능

1. **회원가입/로그인** - JWT 기반 인증
2. **AI 챗봇 대화** - vLLM 서버 연동 (까칠이, 순둥이)
3. **플로팅 챗봇** - 모든 페이지에서 즉시 접근
4. **여행 대시보드** - 개인화된 여행 추천
5. **페르소나 수집** - AI 기반 사용자 선호도 파악

---

## ⚠️ 문제 해결

### 백엔드 서버가 시작되지 않을 때
- MySQL 서버가 켜져있는지 확인
- `192.168.0.222` 서버에 접근 가능한지 확인

### AI 응답이 안 올 때
- pinggy 터널이 활성화되어 있는지 확인
- 캠프 vLLM 서버가 실행 중인지 확인
- 터널 URL이 만료되지 않았는지 확인 (60분 제한)

### 프론트엔드가 백엔드에 연결되지 않을 때
- 백엔드가 8000 포트에서 실행 중인지 확인
- `.env` 파일의 `VITE_API_BASE_URL` 확인
- 브라우저 새로고침 (`Ctrl+F5`)

---

## 📞 문의

문제가 있으면 팀원에게 문의하세요!
