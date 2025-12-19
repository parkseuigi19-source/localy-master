"""통일된 데이터 스키마 - ALL_IN_ONE_GUIDE 표준"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlaceData(BaseModel):
    """모든 장소 데이터의 표준 형식"""
    place_id: str = Field(..., description="Google Place ID")
    name: str
    category: str  # restaurant | cafe | hotel | landmark | shopping
    address: str
    latitude: float
    longitude: float
    region: str
    rating: float = 0
    review_count: int = 0
    price_level: int = 0
    opening_hours: List[str] = []
    open_now: Optional[bool] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    images: List[str] = []
    categorized_images: Dict[str, List[str]] = {}  # Vision API 분류 사진 (선택사항)
    google_maps_url: str
    description: Optional[str] = None
    tags: List[str] = []

class AgentResponse(BaseModel):
    """모든 에이전트의 표준 응답"""
    success: bool
    agent_name: str
    data: List[Dict[str, Any]] = []
    count: int = 0
    message: str
    error: Optional[str] = None

class UserPersona(BaseModel):
    """
    사용자 페르소나 - 회원가입 시 수집, 여행 계획 시 참고용
    
    ⚠️ 중요: 페르소나는 기본 선호도일 뿐!
    - LLM은 페르소나를 참고하되, 매번 사용자에게 확인 필요
    - 예: "평소 한식 좋아하시는데, 이번엔 어떤 음식 드시고 싶으세요?"
    - 사용자가 다른 선택을 할 수 있음 (페르소나 ≠ 강제)
    """
    user_id: str
    age_group: str  # "20대", "30대", "40대", "50대+"
    gender: Optional[str] = None
    travel_style: List[str] = []  # ["힐링", "액티비티", "맛집투어", "문화체험"]
    budget_level: str = "중"  # "저" | "중" | "고"
    food_preferences: List[str] = []  # ["한식", "일식", "양식", "해산물"]
    accommodation_style: str = "호텔"  # "호텔" | "펜션" | "게스트하우스" | "한옥"
    interests: List[str] = []  # ["사진", "쇼핑", "자연", "역사", "카페"]
    created_at: str
    updated_at: str

class TravelState(BaseModel):
    """
    전역 상태 관리 - 여행 계획 전체 정보 저장
    
    Phase 1: 기본 정보만 사용
    Phase 2: 에이전트 간 공유
    Phase 3: LangGraph 워크플로우 전체 상태
    """
    # 기본 정보
    user_id: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    num_travelers: int = 1
    total_budget: Optional[int] = None
    
    # 선택된 지역들
    selected_regions: List[str] = []
    current_region: Optional[str] = None
    
    # 검색 결과 캐시
    search_results: Dict[str, List[PlaceData]] = {}
    
    # 선택된 장소들
    selected_places: Dict[str, List[PlaceData]] = {}  # {category: [places]}
    
    # 대화 기록
    chat_history: List[Dict[str, str]] = []
    
    # 페르소나 (선택사항)
    persona: Optional[UserPersona] = None
    
    # 메타데이터
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed: bool = False


# 테스트
if __name__ == "__main__":
    # PlaceData 테스트
    place = PlaceData(
        place_id="ChIJ123",
        name="테스트 호텔",
        category="hotel",
        address="강원도 강릉시",
        latitude=37.7519,
        longitude=128.8761,
        region="강릉",
        rating=4.5,
        review_count=120,
        google_maps_url="https://maps.google.com"
    )
    print(f"✅ PlaceData 생성 성공: {place.name}")
    
    # AgentResponse 테스트
    response = AgentResponse(
        success=True,
        agent_name="accommodation",
        data=[place.dict()],
        count=1,
        message="숙소 검색 완료!"
    )
    print(f"✅ AgentResponse 생성 성공: {response.message}")
    
    # UserPersona 테스트
    persona = UserPersona(
        user_id="test_user",
        age_group="30대",
        travel_style=["힐링", "맛집투어"],
        food_preferences=["한식", "해산물"],
        accommodation_style="호텔",
        interests=["사진", "자연"],
        created_at="2025-12-05",
        updated_at="2025-12-05"
    )
    print(f"✅ UserPersona 생성 성공: {persona.user_id}")
    
    print("\n🎉 모든 스키마 검증 완료!")
