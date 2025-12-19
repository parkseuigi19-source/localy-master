"""
Travel Flow State Management - V2 (일차별 플로우)
여행 계획 플로우의 상태를 추적하고 관리하는 클래스
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class TravelFlowState:
    """여행 계획 플로우 상태 관리"""
    
    # 플로우 단계 정의
    STEP_DESTINATION = 1      # 목적지 (대분류)
    STEP_REGIONS = 2          # 세부 지역 (소분류)
    STEP_DATES = 3            # 날짜
    STEP_BUDGET = 4           # 예산
    STEP_PEOPLE = 5           # 인원
    STEP_RESTAURANT = 6       # 맛집 선호도
    STEP_CAFE = 7             # 카페 선호도
    STEP_ACCOMMODATION = 8    # 숙소 선호도
    STEP_LANDMARK = 9         # 관광지 선호도
    STEP_ITINERARY = 10       # 일정 생성
    
    def __init__(self):
        """초기화"""
        self.current_step = self.STEP_DESTINATION
        self.is_in_flow = True
        self.paused_step: Optional[int] = None
        
        # 일차별 플로우 관리
        self.current_day = 1
        self.total_days = 0  # 일수 (박수 + 1)
        self.nights = 0      # 박수
        
        # 수집된 정보
        self.collected_info: Dict[str, Any] = {
            'destination': None,
            'regions': [],
            'start_date': None,
            'end_date': None,
            'budget': None,
            'people_count': None,
            'restaurant_preference': [],
            'cafe_preference': [],
            'accommodation_preference': [],
            'landmark_preference': []
        }
        
        # 일차별 선택 항목 {day: {category: [place_ids]}}
        self.daily_selections: Dict[int, Dict[str, List[str]]] = {}
        
        # 에이전트 호출 결과 저장
        self.agent_results: Dict[str, Any] = {
            'region_recommendations': None,
            'restaurant_recommendations': None,
            'cafe_recommendations': None,
            'accommodation_recommendations': None,
            'landmark_recommendations': None
        }
    
    def pause_flow(self) -> None:
        """플로우 일시 정지"""
        self.paused_step = self.current_step
        self.is_in_flow = False
    
    def resume_flow(self) -> None:
        """플로우 재개"""
        if self.paused_step is not None:
            self.current_step = self.paused_step
            self.paused_step = None
        self.is_in_flow = True
    
    def next_step(self) -> None:
        """다음 단계로 이동"""
        if self.current_step < self.STEP_ITINERARY:
            self.current_step += 1
    
    def next_day(self) -> bool:
        """다음 일차로 이동. 모든 일차 완료 시 False 반환"""
        if self.current_day < self.total_days:
            self.current_day += 1
            self.current_step = self.STEP_RESTAURANT  # 맛집부터 다시 시작
            return True
        return False
    
    def is_last_day(self) -> bool:
        """마지막 날인지 확인"""
        return self.current_day == self.total_days
    
    def needs_accommodation(self) -> bool:
        """현재 일차에 숙소가 필요한지 확인 (마지막 날은 불필요)"""
        return self.current_day <= self.nights
    
    def get_excluded_place_ids(self, category: str) -> List[str]:
        """이전 일차에서 선택한 장소 ID 목록 반환 (중복 방지)"""
        excluded = []
        for day in range(1, self.current_day):
            if day in self.daily_selections:
                if category in self.daily_selections[day]:
                    excluded.extend(self.daily_selections[day][category])
        return excluded
    
    def add_selection(self, category: str, place_ids: List[str]) -> None:
        """현재 일차에 선택 항목 추가"""
        if self.current_day not in self.daily_selections:
            self.daily_selections[self.current_day] = {}
        self.daily_selections[self.current_day][category] = place_ids
    
    def is_step_complete(self, step: int) -> bool:
        """특정 단계가 완료되었는지 확인"""
        if step == self.STEP_DESTINATION:
            return self.collected_info['destination'] is not None
        elif step == self.STEP_REGIONS:
            return len(self.collected_info['regions']) > 0
        elif step == self.STEP_DATES:
            return self.collected_info['start_date'] is not None
        elif step == self.STEP_BUDGET:
            return self.collected_info['budget'] is not None
        elif step == self.STEP_PEOPLE:
            return self.collected_info['people_count'] is not None
        elif step == self.STEP_RESTAURANT:
            return len(self.collected_info['restaurant_preference']) > 0
        elif step == self.STEP_CAFE:
            return len(self.collected_info['cafe_preference']) > 0
        elif step == self.STEP_ACCOMMODATION:
            return len(self.collected_info['accommodation_preference']) > 0
        elif step == self.STEP_LANDMARK:
            return len(self.collected_info['landmark_preference']) > 0
        return False
    
    def get_step_name(self, step: Optional[int] = None) -> str:
        """단계 이름 반환"""
        if step is None:
            step = self.current_step
        
        step_names = {
            self.STEP_DESTINATION: "목적지",
            self.STEP_REGIONS: "세부 지역",
            self.STEP_DATES: "날짜",
            self.STEP_BUDGET: "예산",
            self.STEP_PEOPLE: "인원",
            self.STEP_RESTAURANT: "맛집 선호도",
            self.STEP_CAFE: "카페 선호도",
            self.STEP_ACCOMMODATION: "숙소 선호도",
            self.STEP_LANDMARK: "관광지 선호도",
            self.STEP_ITINERARY: "일정 생성"
        }
        return step_names.get(step, "알 수 없음")
    
    def get_context_for_prompt(self) -> str:
        """현재 상태를 Prompt에 추가할 컨텍스트로 변환"""
        context = f"\n\n## 현재 플로우 상태\n"
        context += f"- 현재 단계: {self.current_step}단계 ({self.get_step_name()})\n"
        context += f"- 플로우 내부: {'예' if self.is_in_flow else '아니오 (예외 처리 중)'}\n"
        
        if self.total_days > 0:
            context += f"- 여행 기간: {self.nights}박 {self.total_days}일\n"
            context += f"- 현재 일차: {self.current_day}일차\n"
        
        if self.paused_step:
            context += f"- 중단된 단계: {self.paused_step}단계 ({self.get_step_name(self.paused_step)})\n"
        
        context += f"\n## 수집된 정보\n"
        for key, value in self.collected_info.items():
            if value:
                context += f"- {key}: {value}\n"
        
        if self.daily_selections:
            context += f"\n## 일차별 선택 항목\n"
            for day, selections in self.daily_selections.items():
                if selections:
                    context += f"- {day}일차: {selections}\n"
        
        return context
    
    def should_call_agent(self, step: int) -> bool:
        """특정 단계에서 에이전트를 호출해야 하는지 확인"""
        return step in [
            self.STEP_RESTAURANT,
            self.STEP_CAFE,
            self.STEP_ACCOMMODATION,
            self.STEP_LANDMARK
        ]
    
    def get_agent_query(self, step: int) -> Optional[str]:
        """에이전트 호출을 위한 쿼리 생성"""
        destination = self.collected_info.get('destination', '')
        regions = ' '.join(self.collected_info.get('regions', []))
        location = f"{destination} {regions}".strip()
        
        if step == self.STEP_RESTAURANT:
            preferences = ' '.join(self.collected_info['restaurant_preference'])
            return f"{location} {preferences}".strip()
        elif step == self.STEP_CAFE:
            preferences = ' '.join(self.collected_info['cafe_preference'])
            return f"{location} {preferences}".strip()
        elif step == self.STEP_ACCOMMODATION:
            preferences = ' '.join(self.collected_info['accommodation_preference'])
            return f"{location} {preferences}".strip()
        elif step == self.STEP_LANDMARK:
            preferences = ' '.join(self.collected_info['landmark_preference'])
            return f"{location} {preferences}".strip()
        
        return None


# 세션별 FlowState 저장소
flow_states: Dict[str, TravelFlowState] = {}


def get_flow_state(session_id: str) -> TravelFlowState:
    """세션 ID로 FlowState 가져오기 (없으면 생성)"""
    if session_id not in flow_states:
        flow_states[session_id] = TravelFlowState()
    return flow_states[session_id]


def reset_flow_state(session_id: str) -> None:
    """FlowState 초기화"""
    if session_id in flow_states:
        del flow_states[session_id]
