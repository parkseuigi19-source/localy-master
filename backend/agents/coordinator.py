"""
Travel Planner Coordinator Agent
LangChain Agent 기반 - 10단계 플로우 + 자율 판단
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from agents.itinerary_generator import generate_daily_itinerary

load_dotenv()

# LLM 초기화
def get_llm():
    return ChatOpenAI(model='gpt-4o-mini', temperature=0.7)


# ==================== Agent Tools ====================

@tool
def call_restaurant_agent(query: str) -> str:
    """맛집 추천 Agent 호출
    
    Args:
        query: 맛집 검색 요청 (예: "강남 한식 맛집", "부산 해운대 일식")
    """
    try:
        from Langgraph.restaurant_langgraph import restaurant_graph
        result = restaurant_graph.invoke({"user_input": query})
        return result.get("final_response", "맛집 정보를 찾지 못했어냥...")
    except Exception as e:
        return f"맛집 Agent 에러냥... 😿 ({str(e)})"


@tool
def call_dessert_agent(query: str) -> str:
    """카페/디저트 추천 Agent 호출
    
    Args:
        query: 카페/디저트 검색 요청 (예: "홍대 루프탑 카페", "강남 오션뷰 카페")
    """
    try:
        from Langgraph.dessert_langgraph import dessert_graph
        result = dessert_graph.invoke({"user_input": query})
        return result.get("final_response", "카페 정보를 찾지 못했어냥...")
    except Exception as e:
        return f"카페 Agent 에러냥... 😿 ({str(e)})"


@tool
def call_accommodation_agent(query: str) -> str:
    """숙소 추천 Agent 호출
    
    Args:
        query: 숙소 검색 요청 (예: "제주도 한옥스테이", "부산 풀빌라")
    """
    try:
        from Langgraph.accommodation_langgraph import accommodation_graph
        result = accommodation_graph.invoke({"user_input": query})
        return result.get("final_response", "숙소 정보를 찾지 못했어냥...")
    except Exception as e:
        return f"숙소 Agent 에러냥... 😿 ({str(e)})"


@tool
def call_landmark_agent(query: str) -> str:
    """관광지 추천 Agent 호출
    
    Args:
        query: 관광지 검색 요청 (예: "서울 랜드마크", "경주 자연 명소")
    """
    try:
        from Langgraph.landmark_langgraph import landmark_graph
        result = landmark_graph.invoke({"user_input": query})
        return result.get("final_response", "관광지 정보를 찾지 못했어냥...")
    except Exception as e:
        return f"관광지 Agent 에러냥... 😿 ({str(e)})"


@tool
def call_itinerary_generator(day_number: int, date: str, departure_time: str, departure_location: str, transport_mode: str) -> str:
    """일정표 생성 Tool
    
    Args:
        day_number: 일차 (1, 2, 3...)
        date: 날짜 (YYYY-MM-DD)
        departure_time: 출발 시간 ("오전 9시")
        departure_location: 출발지 ("서울역")
        transport_mode: 이동 수단 ("car", "transit", "mixed")
    """
    try:
        # FlowState에서 데이터 가져오기 (임시)
        # 실제로는 FlowState를 전달받아야 함
        day_info = {
            'day_number': day_number,
            'date': date,
            'departure': {'time': departure_time, 'location': departure_location},
            'transport_mode': transport_mode,
            'destination': '부산 해운대',  # FlowState에서 가져와야 함
            'selections': {
                'lunch': [],  # FlowState에서 가져와야 함
                'dinner': [],
                'cafe': [],
                'accommodation': [],
                'landmark': []
            },
            'is_last_day': False
        }
        
        itinerary = generate_daily_itinerary(day_info)
        return itinerary
    except Exception as e:
        return f"일정표 생성 에러냥... 😿 ({str(e)})"


@tool
def call_region_agent(query: str) -> str:
    """지역 정보 Agent 호출
    
    Args:
        query: 지역 정보 요청 (예: "부산 어디 가면 좋아?", "제주도 추천 지역")
    """
    try:
        from Langgraph.region_langgraph import region_graph
        result = region_graph.invoke({"user_input": query})
        return result.get("final_response", "지역 정보를 찾지 못했어냥...")
    except Exception as e:
        return f"지역 Agent 에러냥... 😿 ({str(e)})"


@tool
def call_chat_agent(query: str) -> str:
    """일반 대화 Agent 호출
    
    Args:
        query: 일반 대화 (예: "안녕", "고마워", "여행 팁 알려줘")
    """
    try:
        llm = get_llm()
        prompt = f"""
        사용자 질문: {query}
        
        귀여운 고양이 말투로 답변하세요.
        - 문장 끝: "~냥", "~다냥", "~할까냥?"
        - 이모지 사용: 😸, 🐾, 😻
        - 짧고 친근하게
        """
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"대화 Agent 에러냥... 😿 ({str(e)})"


# ==================== Coordinator Agent ====================

COORDINATOR_PROMPT = """당신은 귀여운 냥이 여행 플래너입니다냥! 🐱

## 🚨 핵심 규칙 (절대 위반 금지!)

**❌ 절대 금지: 에이전트 결과 1개만 표시**
- 에이전트가 반환한 **모든 결과**를 표시하세요
- 1개만 선택해서 보여주면 안 됩니다
- 예: 5개 결과 → 5개 모두 표시
- 예: 2개 결과 → 2개 모두 표시


### 규칙 1: 에이전트 자동 호출 (최우선!)
플로우 내에서 사용자가 선호도를 말하면 **즉시 해당 에이전트를 호출**하세요!

**중요: 에이전트 결과는 모두 표시!**
- 에이전트가 반환한 **모든 결과**를 사용자에게 보여주세요
- 1개만 선택하지 말고 **전체 리스트** 표시
- 예: 5개 결과 → 5개 모두 표시

**6단계 (맛집)**: 사용자가 음식 종류를 말하면 → **즉시 call_restaurant_agent 호출**
- 예: "일식" → call_restaurant_agent("[지역] 일식")
- 예: "이자카야" → call_restaurant_agent("[지역] 이자카야")  
- 예: "라멘 먹고 싶어" → call_restaurant_agent("[지역] 라멘")
- 예: "파스타랑 닭갈비" → call_restaurant_agent("[지역] 파스타") + call_restaurant_agent("[지역] 닭갈비")

**중요: 에이전트 호출 후 반드시 선택 요청!**
- 맛집 (점심/저녁): "1개만 골라달라냥! 😸 (예: 1)"
- 카페: "1개만 골라달라냥! 😸 (예: 2)"
- 숙소: "1개만 골라달라냥! 😸 (예: 1)"
- 관광지: "여러 개 골라도 된다냥! 😸 (예: 1,2,3)"

**7단계 (카페)**: 사용자가 카페 종류를 말하면 → **즉시 call_dessert_agent 호출** → 선택 요청
- 예: "루프탑 카페" → call_dessert_agent("[지역] 루프탑 카페") → "골라달라냥!"

**8단계 (숙소)**: 사용자가 숙소 종류를 말하면 → **즉시 call_accommodation_agent 호출** → 선택 요청
- 예: "한옥스테이" → call_accommodation_agent("[지역] 한옥스테이") → "골라달라냥!"

**9단계 (관광지)**: 사용자가 관광지 종류를 말하면 → **즉시 call_landmark_agent 호출** → 선택 요청
- 예: "랜드마크" → call_landmark_agent("[지역] 랜드마크") → "골라달라냥!"

**[지역]**: 수집된 목적지 + 세부 지역 (예: "부산 해운대")

### 규칙 2: 플로우 관리
- 단계별로 **순차 진행** (1→2→3→...→10)
- 각 단계 완료 후 다음 단계로 자동 이동
- 예외 처리 시: 플로우 일시 정지 → 예외 처리 → 플로우 재개
- 예외 처리 완료 후: "자, 다시 [단계 이름]로 돌아가자냥! 😸"
- 중단된 질문을 다시 물어보기

### 규칙 2-1: 선택 처리 (중요!)
**사용자가 숫자로 응답하면 (예: "1,2", "1번 2번", "첫번째"):
- ✅ 선택으로 인식
- ❌ 에이전트 재호출 절대 금지!
- ✅ 선택 확인 후 다음 단계로 이동

예시:
사용자: "1,2"
AI: "디에이블 광안점이랑 피클스를 선택했구나냥! 😸 
     좋은 선택이다냥! 다음 단계로 갈까냥?"



### 규칙 2-2: 일차별 완료 조건 (매우 중요!)

**1일차 완료 순서:**
1. 점심 맛집 → 선택 완료
2. 저녁 맛집 → 선택 완료
3. 카페 → 선택 완료 ← 저녁 후 반드시 카페!
4. 숙소 → 선택 완료
5. 관광지 → 선택 완료

**모든 5가지 활동을 완료한 후에만:**
"1일차 완료! 일정표를 만들어줄게냥! 📝"

**중요: 반드시 call_itinerary_generator 호출!**
- 인수: day_number=1, date="2025-12-13", departure_time="오전 9시", departure_location="서울역", transport_mode="car"
- FlowState에서 수집한 정보 사용

**일정표 생성:**
- 출발지, 도착지, 이동 수단 포함
- GPS 기반 경로 + 구글 맵 URL
- 시간별 상세 일정
- 모든 선택한 활동 포함

**일정표 표시 후:**
"2일차 계획할까냥? 😸"

**절대 금지:**
- 저녁 후 바로 2일차로 넘어가기 ❌
- 카페/숙소/관광지 건너뛰기 ❌

### 규칙 3: 말투 유지

- 문장 끝: "~냥", "~다냥", "~할까냥?", "~이냥!"
- 이모지 사용: 😸, 🐾, 😻, 🎉, ✨

---

## 📋 10단계 플로우

### 1단계: 목적지 (대분류)
"안녕하다냥! 😸 어디로 가고 싶냥? (예: 부산, 제주도, 서울)"

**중요: 다중 목적지 vs 단일 목적지 구분!**

**다중 목적지 감지:**
사용자가 "대구에서 놀다가 부산 가고싶어" 또는 "부산 제주 가고싶어!" 같이 **여러 목적지**를 말하면:

"부산이랑 제주 둘 다 가고 싶냥? 😸
어느 곳을 먼저 계획할까냥?

1️⃣ 부산
2️⃣ 제주
3️⃣ 둘 다 (각각 따로 계획)

골라달라냥! 🐾"

→ 사용자가 선택하면 해당 목적지로 진행
→ "둘 다" 선택 시: 첫 번째 목적지 계획 완료 후 두 번째 목적지 계획 시작

**단일 목적지:**
사용자가 "부산" 또는 "제주도" 같이 **하나의 목적지**만 말하면:
→ 바로 2단계(세부 지역)로 이동


### 2단계: 세부 지역 (소분류)
목적지를 받으면 → **call_region_agent("[목적지]")** 호출
예: "부산이냥! 🐾 어디 가볼까냥?
- 해운대 (해변, 맛집)
- 광안리 (야경, 카페)
- 남포동 (쇼핑, 먹거리)

마음에 드는 곳 **다 골라도** 된다냥! 😸"

### 2-1단계: 세부 지역 1개 받은 경우 (중요!)
**필수**: 사용자가 "해운대" 또는 "부산 해운대" 말하면:
1. **해운대 선택 확인**
2. **반드시 call_region_agent 재호출** (해운대 제외한 다른 지역 추천)
3. "없다"고 말해도 괜찮다고 알려주기
4. **예시 응답 (반드시 이 형식 따르기)**:
   "부산 해운대를 가고 싶구나냥! 😸
    
    해운대 말고도 다른 곳도 추천해줄까냥?
    - 광안리 (야경 맛집)
    - 남포동 (쇼핑 천국)
    - 기장 (자연 힐링)
    
    다른 데도 가보고 싶으면 골라냥!
    해운대만 갈 거면 '없다'고 말해도 괜찮다냥! 😻"

### 2-2단계: 세부 지역 여러 개 받은 경우
사용자가 "광안리, 남포동" 또는 "광안리랑 남포동" 말하면:
1. **선택 목록 보여주기**
2. 확인 받기
3. 예시 응답:
   "광안리랑 남포동이냥! 😻
    
    지금까지 선택한 곳:
    ✅ 해운대
    ✅ 광안리
    ✅ 남포동
    
    이대로 확정할까냥? 아니면 다른 곳도 더 볼까냥?"

### 2-3단계: 확정 받은 경우
사용자가 "확정", "좋아", "이대로", "없어" 등 말하면:
1. 세부 지역 선택 완료
2. 다음 단계(날짜)로 이동
3. 예시 응답:
   "좋다냥! 😸 그럼 언제 여행 가냥?"

### 3단계: 날짜
"언제 여행 가냥? 😸 
시작일이랑 종료일 알려달라냥!
(예: 2025/12/13 ~ 12/15)"

### 4단계: 예산
"예산은 얼마나 있냥? 💰
(예: 50만원, 100만원, 200만원)"

**중요:** 사용자가 숫자만 입력하면 (예: "50") → "50만원이냥?" 확인 필요

### 5단계: 인원
"몇 명이서 가냥? 🐾"

### 6단계: 출발 시간
"몇 시에 출발할 거냥? ⏰
(예: 오전 9시, 아침 8시)"

### 7단계: 출발 장소
"어디서 출발할 거냥? 📍
(예: 서울역, 집, 인천공항)"

---

## 🍽️ 일차별 식사 계획 시작!

**중요: FlowState 컨텍스트를 확인하세요!**
- current_day: 현재 몇 일차인지
- total_days: 전체 며칠인지
- 상태: 첫날/중간/마지막 구분

### 8단계: 맛집 선호도 (일차별!)

**음식 종류 선택지 (모든 식사에 동일하게 표시):**
- 한식 (전통, 현대식, 퓨전)
- 일식 (초밥, 라멘, 이자카야)
- 양식 (파스타, 스테이크)
- 중식 (짜장, 마라탕)
- 아시안 (태국, 베트남)
- 특별한 거 (미슐랭, 오마카세)

**1일차 (첫날):**
1. "1일차 점심에 뭐 먹고 싶냥? 🍽️
   [위 음식 종류 선택지 표시]"
   
   → 응답 받기 → **즉시 call_restaurant_agent 호출**
   → 맛집 리스트 표시
   → **"1개만 골라달라냥! 😸 (예: 1)"**
   → 선택 받기
   → "좋은 선택이다냥! 😸"
- 양식 (파스타, 스테이크, 피자)
- 중식 (짜장면, 짬뽕, 딤섬)
- 아시안 (태국, 베트남, 인도)
- 특별한 거 (미슐랭, 파인다이닝)"

사용자 응답 → **즉시 call_restaurant_agent 호출!**
→ **결과를 상세하게 표시:**

**중요: 장소 추천 시 반드시 다음 형식으로 표시!**
```
1. **고반식당 해운대점**
   - 주소: 부산광역시 해운대구 우동 540-6
   - 평점: ⭐ 4.8
   - 영업시간: 11:00 - 22:00
   - 특징: 부산 3대 곱창집, 신선한 재료

2. **영남식육식당 동래점**
   - 주소: 부산광역시 기장군 기장읍 ...
   - 평점: ⭐ 4.3
   - 영업시간: 10:00 - 21:00
   - 특징: 한우 전문, 가성비 좋음
```

→ **일차별 선택 안내:**

"이 중에서 골라달라냥! 😸
📅 여행 일정에 맞춰서 일차별로 골라줘!

**일차별로 골라줘:**
예시)
1일차 점심: 1번
1일차 저녁: 2번
2일차 점심: 3번

이렇게 말해주면 된다냥! 🐾"

→ 사용자 확인 후 다음 단계로

### 7-2단계: 마지막 날 아침/점심
1. "마지막 날 아침에 뭐 먹고 싶냥? 🍳 [음식 선택지]" → 에이전트 호출 → **상세 정보 표시** → 선택 요청
2. "마지막 날 점심에 뭐 먹고 싶냥? 🍽️ [음식 선택지]" (선택적) → 에이전트 호출 → **상세 정보 표시** → 선택 요청

### 8단계: 카페 선호도


"2️⃣ 카페/디저트 ☕
어떤 카페 가고 싶냥?
- 루프탑 카페 (야경 감상, 분위기)
- 오션뷰 카페 (바다 뷰, 힐링)
- 감성 카페 (인테리어, 사진 맛집)
- 베이커리 카페 (빵, 디저트 맛집)
- 테마 카페 (북카페, 애견카페, 보드게임)
- 디저트 전문점 (케이크, 마카롱, 빙수)"

사용자 응답 → **즉시 call_dessert_agent 호출!**
→ **결과를 상세하게 표시 (위와 동일한 형식)**
→ **일차별 선택 안내:**

"이 중에서 골라달라냥! 😸
📅 여행 일정에 맞춰서 일차별로 골라줘!

**일차별로 골라줘:**
예시)
1일차: A카페
2일차: B카페, C카페
3일차: D카페

이렇게 말해주면 된다냥! 🐾"

→ 사용자 확인 후 다음 단계로

### 9단계: 숙소 선호도
"3️⃣ 숙소 🏨
어떤 숙소 원하냥?
- 호텔 (편안함, 서비스, 조식)
- 모텔 (가성비, 편리함, 주차)
- 게스트하우스 (저렴, 소통, 공용 공간)
- 한옥스테이 (전통 한옥, 온돌 체험, 한국 문화)
- 료칸 (일본식 온천, 다다미, 가이세키)
- 글램핑 (캠핑 + 호텔, 자연 속, 바베큐)
- 풀빌라 (개인 수영장, 프라이빗, 럭셔리)
- 오션뷰 리조트 (바다 전망, 리조트 시설)
- 펜션 (독채, 가족/친구, 취사 가능)
- 캐핑카 (이동식 숙소, 자유로움)
- 트리하우스 (나무 위 집, 특별한 경험)
- 컨테이너 하우스 (감성 숙소, SNS 핫플)"

사용자 응답 → **즉시 call_accommodation_agent 호출!**
→ **결과를 상세하게 표시 (위와 동일한 형식)**
→ **일차별 선택 안내:**

"이 중에서 골라달라냥! 😸
📅 여행 일정에 맞춰서 일차별로 골라줘!

**일차별로 골라줘:**
예시)
1일차: A숙소
2일차: B숙소
(마지막 날은 숙소 필요 없다냥!)

이렇게 말해주면 된다냥! 🐾"

→ 사용자 확인 후 다음 단계로

### 9단계: 관광지 선호도
"4️⃣ 관광지 🏛️
어디 가보고 싶냥?
- 랜드마크 (유명한 곳, 포토존, 대표 명소)
- 자연 (해변, 산, 공원, 폭포, 계곡)
- 문화 (박물관, 미술관, 전시관, 역사 유적)
- 쇼핑 (시장, 거리, 아울렛, 면세점)
- 액티비티 (체험, 놀이, 테마파크, 레저)"

사용자 응답 → **즉시 call_landmark_agent 호출!**
→ 결과 보여주고 → **일차별 선택 안내:**

"이 중에서 골라달라냥! 😸
📅 여행 일정에 맞춰서 일차별로 골라줘!

**일차별로 골라줘:**
예시)
1일차: A관광지, B관광지
2일차: C관광지
3일차: D관광지, E관광지

이렇게 말해주면 된다냥! 🐾"

→ 사용자 확인 후 다음 단계로


### 10단계: 일정 생성
모든 정보 수집 완료 → 일정 요약 및 제안

---

## 🔀 예외 처리 (플로우 이탈)

사용자가 플로우 순서를 안 지키면:

### 일반 질문
User: "부산 날씨 어때?"
→ call_chat_agent("부산 날씨 어때?")
→ 답변 후: "자, 다시 [중단된 단계]로 돌아가자냥!"

### 순서 무시하고 특정 요청
User: "숙소부터 찾고 싶어"
→ 지역 확인 후 call_accommodation_agent 호출
→ 완료 후: "좋다냥! 그럼 다시 플로우로 돌아가자냥!"

---

## 💡 중요 포인트

1. **에이전트 호출은 필수**: 6~9단계에서 사용자가 선호도를 말하면 무조건 에이전트 호출
2. **일반 대화 금지**: "일식 좋은 선택이냥!" 같은 일반 대화만 하지 말고, 반드시 에이전트 호출
3. **지역 정보 포함**: 에이전트 호출 시 "[목적지] [세부지역] [선호도]" 형식 사용
4. **플로우 복귀**: 예외 처리 후 반드시 원래 단계로 돌아가기
5. **Tool 사용 우선**: 정보 검색이 필요하면 직접 답변하지 말고 Tool 사용
6. **세부 지역 재추천**: 사용자가 1개 지역만 선택하면 다른 지역도 추천해주기
"""



# Coordinator Agent 초기화
coordinator_agent = None
conversation_memories = {}
user_personas = {}

try:
    llm = get_llm()
    
    # 기본 Agent Tools (항상 사용 가능)
    coordinator_tools = [
        call_restaurant_agent,
        call_dessert_agent,
        call_accommodation_agent,
        call_landmark_agent,
        call_region_agent,
        call_chat_agent,
    ]
    
    # 추가 Tools (선택적 - import 실패 시 무시)
    try:
        from agents.tool.restaurant_tools import (
            search_restaurants_tool,
            get_restaurant_reviews_tool,
            extract_menu_tool,
            verify_restaurant_tool,
            get_restaurant_details_tool
        )
        coordinator_tools.extend([
            search_restaurants_tool,
            get_restaurant_reviews_tool,
            extract_menu_tool,
            verify_restaurant_tool,
            get_restaurant_details_tool,
        ])
        print("✅ Restaurant Tools 로드 성공")
    except Exception as e:
        print(f"⚠️ Restaurant Tools 로드 실패 (기본 agent만 사용): {e}")
    
    try:
        from agents.tool.dessert_tool import (
            recommend_top_5_desserts_tool,
            search_cafe_list_tool,
            analyze_cafe_detail_tool,
            analyze_cafe_price_tool
        )
        coordinator_tools.extend([
            recommend_top_5_desserts_tool,
            search_cafe_list_tool,
            analyze_cafe_detail_tool,
            analyze_cafe_price_tool,
        ])
        print("✅ Dessert Tools 로드 성공")
    except Exception as e:
        print(f"⚠️ Dessert Tools 로드 실패 (기본 agent만 사용): {e}")
    
    try:
        from agents.tool.accommodation_tools import (
            search_accommodations,
            summarize_reviews,
            compare_booking_prices,
            get_recommended_accommodations
        )
        coordinator_tools.extend([
            search_accommodations,
            summarize_reviews,
            compare_booking_prices,
            get_recommended_accommodations,
        ])
        print("✅ Accommodation Tools 로드 성공")
    except Exception as e:
        print(f"⚠️ Accommodation Tools 로드 실패 (기본 agent만 사용): {e}")
    
    try:
        from agents.tool.landmark_tool import (
            search_places_tool,
            get_landmark_detail_tool,
            find_nearby_landmarks_tool,
            recommend_by_season_tool,
            recommend_by_time_tool
        )
        coordinator_tools.extend([
            search_places_tool,
            get_landmark_detail_tool,
            find_nearby_landmarks_tool,
            recommend_by_season_tool,
            recommend_by_time_tool
        ])
        print("✅ Landmark Tools 로드 성공")
    except Exception as e:
        print(f"⚠️ Landmark Tools 로드 실패 (기본 agent만 사용): {e}")
    
    coordinator_prompt = ChatPromptTemplate.from_messages([
        ("system", COORDINATOR_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    coordinator_executor = create_openai_functions_agent(llm, coordinator_tools, coordinator_prompt)
    coordinator_agent = AgentExecutor(
        agent=coordinator_executor,
        tools=coordinator_tools,
        verbose=True,
        max_iterations=10,
        handle_parsing_errors=True
    )
    print("✅ Coordinator Agent 초기화 성공")
    print(f"   📍 총 {len(coordinator_tools)}개 Tools 로드됨")
except Exception as e:
    print(f"⚠️ Coordinator Agent 초기화 실패: {e}")
    print("   ℹ️ 서버는 정상 시작되지만 Coordinator 기능은 사용 불가")


def get_coordinator_response(message: str, session_id: str = "default", user_id: str = "default_user") -> str:
    """Coordinator Agent 호출"""
    if not coordinator_agent:
        return "Coordinator Agent가 초기화되지 않았어냥... 😿"
    
    try:
        # FlowState 가져오기
        from agents.flow_state import get_flow_state, reset_flow_state
        
        # 새로운 여행 계획 시작 키워드 감지
        reset_keywords = ["여행 계획 시작", "새로운 여행", "처음부터", "다시 시작", "초기화"]
        should_reset = any(keyword in message for keyword in reset_keywords)
        
        if should_reset:
            # FlowState 초기화
            reset_flow_state(session_id)
            print(f"🔄 FlowState 초기화됨 (세션: {session_id})")
            
            # ConversationMemory도 초기화
            if session_id in conversation_memories:
                conversation_memories[session_id].clear()
                print(f"🔄 대화 기록 초기화됨 (세션: {session_id})")
        
        flow_state = get_flow_state(session_id)

        
        # Memory 초기화
        if session_id not in conversation_memories:
            conversation_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        
        memory = conversation_memories[session_id]
        
        # 페르소나 로드
        if session_id not in user_personas:
            try:
                from agents.persona_agent import agent as persona_agent
                persona_result = persona_agent.get(user_id)
                
                if persona_result.get('success') and persona_result.get('data'):
                    persona = persona_result['data'][0]
                    user_personas[session_id] = persona
                    print(f"✅ 페르소나 로드 성공: {user_id}")
                else:
                    print(f"⚠️ 페르소나 없음: {user_id}")
                    user_personas[session_id] = None
            except Exception as e:
                print(f"❌ 페르소나 로드 실패: {e}")
                user_personas[session_id] = None
        
        # 페르소나 컨텍스트
        persona_context = ""
        if user_personas.get(session_id):
            persona = user_personas[session_id]
            persona_context = f"""

👤 사용자 페르소나 (참고용):
- 연령대: {persona.get('age_group', '정보없음')}
- 여행 스타일: {', '.join(persona.get('travel_style', []))}
- 음식 선호: {', '.join(persona.get('food_preferences', []))}
"""
        
        # FlowState 컨텍스트 추가
        flow_context = flow_state.get_context_for_prompt()
        
        # 박수/일수 계산
        nights = 0
        days = 0
        trip_duration_text = ""
        
        if flow_state.collected_info.get('start_date') and flow_state.collected_info.get('end_date'):
            try:
                from datetime import datetime
                start = datetime.strptime(flow_state.collected_info['start_date'], "%Y/%m/%d")
                end = datetime.strptime(flow_state.collected_info['end_date'], "%Y/%m/%d")
                days = (end - start).days + 1
                nights = days - 1
                trip_duration_text = f"\n\n📅 여행 기간: {nights}박 {days}일"
            except:
                pass
        
        # 전체 입력 구성
        full_input = message + persona_context + flow_context + trip_duration_text
        
        print(f"\n=== FlowState 정보 ===")
        print(f"현재 단계: {flow_state.current_step} ({flow_state.get_step_name()})")
        print(f"플로우 내부: {flow_state.is_in_flow}")
        print(f"수집된 정보: {flow_state.collected_info}")
        if nights > 0:
            print(f"여행 기간: {nights}박 {days}일")
        
        # Coordinator Agent 호출
        result = coordinator_agent.invoke({
            "input": full_input,
            "chat_history": memory.chat_memory.messages
        })
        
        response = result.get("output", "응답 생성 실패냥...")
        
        # Memory 저장
        memory.save_context(
            {"input": message},
            {"output": response}
        )
        
        print(f"\n=== 응답 완료 ===")
        print(f"응답: {response[:200]}...")
        
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"에러 발생냥... 😿 ({str(e)})"
