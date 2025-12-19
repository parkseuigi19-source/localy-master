"""LangGraph 상태 스키마 - Supervisor Pattern"""
from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage


class TravelPlannerState(TypedDict):
    """여행 플래너 통합 상태 - Supervisor Pattern + 3-Phase 정보 수집"""
    
    # 대화 관리
    messages: List[BaseMessage]
    user_input: str
    current_phase: str  # "required_info" | "preference_gathering" | "itinerary_generation"
    
    # Phase 1: 필수 정보 (초기 수집)
    required_info: Dict[str, Optional[str]]  # {destination, departure, departure_time, dates, budget}
    required_info_complete: bool
    
    # Phase 2: 선호도 및 선택 (자유 수집)
    preferences: Dict[str, Any]  # 음식, 숙소, 활동 선호도
    selected_items: Dict[str, List[Dict]]  # 사용자가 선택한 항목들 {restaurants: [...], cafes: [...], ...}
    
    # 에이전트 결과 (추천 목록)
    agent_results: Dict[str, Any]  # {restaurant: [...], landmark: [...], ...}
    
    # Phase 3: 최종 일정
    itinerary: Optional[Dict]
    
    # 라우팅
    next_agent: Optional[str]  # 다음에 호출할 에이전트
    
    # 최종 응답 (고양이 말투)
    final_response: str
