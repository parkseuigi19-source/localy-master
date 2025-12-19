"""LangGraph 통합 워크플로우 - Supervisor Pattern"""
from typing import Literal, Optional, Dict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import os

from agents.state import TravelPlannerState

# 환경 변수 로드 (상위 디렉토리의 env 파일)
env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'env')
load_dotenv(env_path)


# LLM을 함수 내부에서 초기화하도록 변경 (lazy initialization)
def get_llm():
    """LLM 인스턴스를 반환합니다 (lazy initialization)"""
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ============================================================================
# Phase 1: 필수 정보 수집
# ============================================================================

def check_missing_required_info(required_info: Dict) -> Optional[str]:
    """필수 정보 중 누락된 것 확인"""
    required_fields = {
        "destination": "목적지",
        "departure": "출발지",
        "departure_time": "출발 시간",
        "dates": "여행 날짜/기간",
        "budget": "예산"
    }
    
    for field, korean_name in required_fields.items():
        if not required_info.get(field):
            return korean_name
    return None


def extract_required_info(user_input: str, current_info: Dict) -> Dict:
    """사용자 입력에서 필수 정보 추출"""
    llm = get_llm()
    
    prompt = f"""
    사용자 입력: "{user_input}"
    현재 수집된 정보: {current_info}
    
    다음 정보 중 사용자 입력에서 추출할 수 있는 것을 JSON 형식으로 반환하세요:
    - destination: 목적지 (예: "부산", "제주도")
    - departure: 출발지 (예: "서울", "인천")
    - departure_time: 출발 시간 (예: "아침 9시", "오후 2시")
    - dates: 여행 날짜/기간 (예: "이번 주말", "12월 15일-17일")
    - budget: 예산 (예: "50만원", "100만원")
    
    추출할 수 없는 정보는 null로 반환하세요.
    JSON만 반환하세요:
    """
    
    response = llm.invoke(prompt)
    try:
        import json
        extracted = json.loads(response.content)
        # 기존 정보와 병합
        for key, value in extracted.items():
            if value and value != "null":
                current_info[key] = value
    except:
        pass
    
    return current_info


# ============================================================================
# Phase 2: 의도 파악 및 에이전트 라우팅
# ============================================================================

def classify_intent_with_llm(user_input: str) -> str:
    """LLM이 사용자 의도 파악"""
    llm = get_llm()
    
    prompt = f"""
    사용자 입력: "{user_input}"
    
    의도를 파악하세요:
    - restaurant: 맛집, 음식점 관련
    - dessert: 디저트, 카페 관련
    - accommodation: 숙소, 호텔 관련
    - landmark: 관광지, 명소 관련
    - region: 지역 추천 관련
    - select: 사용자가 항목을 선택함 (예: "첫 번째", "2번", "이거 좋아")
    - itinerary: 일정 생성 요청
    - chat: 일반 대화
    
    의도만 답하세요 (한 단어):
    """
    
    response = llm.invoke(prompt)
    return response.content.strip().lower()


# ============================================================================
# Supervisor Node
# ============================================================================

def supervisor_node(state: TravelPlannerState) -> TravelPlannerState:
    """
    Supervisor: 대화 관리 + 의도 파악 + 라우팅
    
    1. Phase 확인
    2. 필수 정보 수집 완료 여부 체크
    3. 사용자 의도 파악
    4. 적절한 에이전트로 라우팅 또는 직접 응답
    """
    llm = get_llm()
    user_input = state["user_input"]
    
    # Phase 1: 필수 정보 수집
    if not state.get("required_info_complete", False):
        # 사용자 입력에서 정보 추출
        state["required_info"] = extract_required_info(
            user_input, 
            state.get("required_info", {})
        )
        
        # 누락된 정보 확인
        missing = check_missing_required_info(state["required_info"])
        
        if missing:
            # 목적지 질문 시 Region Agent 호출
            if "destination" in missing or "목적지" in missing:
                prompt = f"""
                사용자에게 어디로 여행 가고 싶은지 물어보세요.
                
                규칙:
                - 짧고 간결하게
                - 예시 포함: "예: 부산, 제주도, 강릉 등"
                - 고양이 말투: 문장 끝에만 "냥" 붙이기
                - 예시: "어디로 가고 싶다냥? (예: 부산, 제주도, 강릉 등)"
                """
                response = llm.invoke(prompt)
                state["final_response"] = response.content
                state["next_agent"] = "region"  # Region Agent 호출
                return state
            
            # 부족한 정보 질문
            prompt = f"""
            사용자에게 {missing} 정보를 물어보세요.
            
            규칙:
            - 매우 짧고 간결하게 (한 문장)
            - 고양이 말투: 문장 끝에만 "냥" 붙이기
            - 예시: "언제 출발한다냥?", "예산은 얼마냥?"
            """
            response = llm.invoke(prompt)
            state["final_response"] = response.content
            state["next_agent"] = "chat"  # 직접 응답
            return state
        else:
            # 필수 정보 수집 완료
            state["required_info_complete"] = True
            state["current_phase"] = "preference_gathering"
            
            # 환영 메시지
            dest = state["required_info"]["destination"]
            prompt = f"""
            사용자가 {dest} 여행을 계획하고 있습니다.
            필수 정보를 모두 받았으니, 이제 맛집, 카페, 숙소, 관광지 등을 추천해줄 수 있다고 알려주세요.
            귀여운 고양이 말투로 (~냥) 친근하게 말하세요.
            """
            response = llm.invoke(prompt)
            state["final_response"] = response.content
            state["next_agent"] = "chat"
            return state
    
    # Phase 2: 선호도 수집 - 의도 파악
    intent = classify_intent_with_llm(user_input)
    state["next_agent"] = intent
    
    return state


# ============================================================================
# 에이전트 노드들
# ============================================================================

def restaurant_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """Restaurant ReAct Agent 호출"""
    try:
        from Langgraph.restaurant_langgraph import restaurant_graph
        
        result = restaurant_graph.invoke({
            "messages": [("user", state["user_input"])]
        })
        
        state["agent_results"]["restaurant"] = result
        state["final_response"] = result["messages"][-1].content
    except Exception as e:
        state["final_response"] = f"맛집 정보를 찾는 중 문제가 생겼어냥... 😿 ({str(e)})"
    
    return state


def landmark_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """Landmark Agent 호출"""
    try:
        from Langgraph.landmark_langgraph import LandmarkWorkflow
        
        workflow = LandmarkWorkflow()
        response = workflow.run(state["user_input"])
        
        state["agent_results"]["landmark"] = {"response": response}
        state["final_response"] = response
    except Exception as e:
        state["final_response"] = f"관광지 정보를 찾는 중 문제가 생겼어냥... 😿 ({str(e)})"
    
    return state


def region_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """Region Agent 호출"""
    try:
        from Langgraph.region_langgraph import region_graph
        
        destination = state.get("required_info", {}).get("destination", "부산")
        
        result = region_graph.invoke({
            "user_input": state["user_input"],
            "destination": destination
        })
        
        state["agent_results"]["region"] = result
        state["final_response"] = result.get("final_response", "지역 정보를 찾았어냥!")
    except Exception as e:
        state["final_response"] = f"지역 정보를 찾는 중 문제가 생겼어냥... 😿 ({str(e)})"
    
    return state


def dessert_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """Dessert/Cafe ReAct Agent 호출"""
    try:
        from Langgraph.dessert_langgraph import dessert_graph
        
        result = dessert_graph.invoke({
            "messages": [("user", state["user_input"])]
        })
        
        state["agent_results"]["dessert"] = result
        state["final_response"] = result["messages"][-1].content
    except Exception as e:
        state["final_response"] = f"디저트/카페 정보를 찾는 중 문제가 생겴어냭... 😿 ({str(e)})"
    
    return state


def accommodation_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """Accommodation ReAct Agent 호출"""
    try:
        from Langgraph.accommodation_langgraph import accommodation_graph
        
        result = accommodation_graph.invoke({
            "messages": [("user", state["user_input"])]
        })
        
        state["agent_results"]["accommodation"] = result
        state["final_response"] = result["messages"][-1].content
    except Exception as e:
        state["final_response"] = f"숙소 정보를 찾는 중 문제가 생겴어냭... 😿 ({str(e)})"
    
    return state


def chat_agent_node(state: TravelPlannerState) -> TravelPlannerState:
    """일반 대화 처리"""
    # final_response가 이미 설정되어 있으면 그대로 사용
    if not state.get("final_response"):
        llm = get_llm()
        prompt = f"사용자 질문: {state['user_input']}\n\n친절하게 답변해주세요."
        response = llm.invoke(prompt)
        state["final_response"] = response.content
    
    return state


# ============================================================================
# 고양이 말투 변환 노드
# ============================================================================

def cat_speech_node(state: TravelPlannerState) -> TravelPlannerState:
    """모든 응답을 고양이 말투로 변환"""
    llm = get_llm()
    original = state["final_response"]
    
    # 이미 고양이 말투면 그대로 반환
    if "냥" in original:
        return state
    
    prompt = f"""
    다음 텍스트를 귀여운 고양이 말투로 변환하세요.
    
    규칙:
    - 문장 끝: "~냥", "~이냥?", "~하냥", "~다냥" 등
    - 자연스럽고 귀여운 느낌
    - 내용은 그대로 유지
    - 너무 과하지 않게 (모든 문장에 냥을 붙이지 말고 적절히)
    
    원본: {original}
    
    고양이 말투:
    """
    
    response = llm.invoke(prompt)
    state["final_response"] = response.content
    
    return state


# ============================================================================
# 그래프 구성
# ============================================================================

def route_to_agent(state: TravelPlannerState) -> str:
    """다음 노드 결정"""
    next_agent = state.get("next_agent", "chat")
    
    # 지원하는 에이전트 목록
    supported_agents = ["restaurant", "landmark", "region", "dessert", "accommodation", "chat"]
    
    if next_agent in supported_agents:
        return next_agent
    else:
        return "chat"


# 그래프 생성
workflow = StateGraph(TravelPlannerState)

# 노드 추가
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("restaurant", restaurant_agent_node)
workflow.add_node("landmark", landmark_agent_node)
workflow.add_node("region", region_agent_node)
workflow.add_node("dessert", dessert_agent_node)
workflow.add_node("accommodation", accommodation_agent_node)
workflow.add_node("chat", chat_agent_node)
workflow.add_node("cat_speech", cat_speech_node)

# 시작점
workflow.set_entry_point("supervisor")

# Supervisor → 각 에이전트 (조건부)
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "restaurant": "restaurant",
        "landmark": "landmark",
        "region": "region",
        "dessert": "dessert",
        "accommodation": "accommodation",
        "chat": "chat"
    }
)

# 각 에이전트 → 고양이 말투 변환
workflow.add_edge("restaurant", "cat_speech")
workflow.add_edge("landmark", "cat_speech")
workflow.add_edge("region", "cat_speech")
workflow.add_edge("dessert", "cat_speech")
workflow.add_edge("accommodation", "cat_speech")
workflow.add_edge("chat", "cat_speech")

# 고양이 말투 → END
workflow.add_edge("cat_speech", END)

# 컴파일
travel_planner_graph = workflow.compile()


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🐱 Travel Planner Graph 테스트")
    print("=" * 60)
    
    # 초기 상태
    initial_state = {
        "messages": [],
        "user_input": "여행 가고 싶어",
        "current_phase": "required_info",
        "required_info": {},
        "required_info_complete": False,
        "preferences": {},
        "selected_items": {},
        "agent_results": {},
        "itinerary": None,
        "next_agent": None,
        "final_response": ""
    }
    
    result = travel_planner_graph.invoke(initial_state)
    print(f"\n응답: {result['final_response']}")
    print("\n완료!")
