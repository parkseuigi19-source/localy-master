"""데이터 모델 스키마 (Pydantic)"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserPersona(BaseModel):
    """사용자 페르소나 정보"""
    budget_level: str = Field(default="중", description="예산 레벨: 저/중/고")
    interests: List[str] = Field(default_factory=list, description="관심사 리스트 (예: ['카페', '사진', '힐링'])")
    
    # 🆕 알레르기 정보
    allergies: List[str] = Field(
        default_factory=list, 
        description="알레르기 재료 리스트 (예: ['땅콩', '우유', '새우', '밀가루'])"
    )
    
    # 🆕 다이어트 모드
    is_diet_mode: bool = Field(
        default=False, 
        description="다이어트 모드 여부 (True면 칼로리/단백질 정보 제공)"
    )
    
    # 🆕 다이어트 목표 (선택사항)
    diet_goal: Optional[str] = Field(
        default=None,
        description="다이어트 목표 (예: '체중감량', '근육증가', '유지')"
    )
    
    # 🆕 일일 목표 칼로리 (선택사항)
    daily_calorie_goal: Optional[int] = Field(
        default=None,
        description="일일 목표 칼로리 (예: 1500, 2000)"
    )
    
    # 🆕 일일 목표 단백질 (선택사항)
    daily_protein_goal: Optional[int] = Field(
        default=None,
        description="일일 목표 단백질 g (예: 80, 120)"
    )

class PlaceData(BaseModel):
    """장소 데이터"""
    place_id: str
    name: str
    category: str
    address: str
    latitude: float
    longitude: float
    region: str
    rating: float = 0.0
    review_count: int = 0
    price_level: int = 0
    tags: List[str] = Field(default_factory=list)
    description: str = ""
    google_maps_url: str = ""
    
    # 🆕 영업 정보
    open_now: Optional[bool] = Field(default=None, description="현재 영업 중 여부")
    opening_hours: Optional[List[str]] = Field(default=None, description="영업 시간 정보")
    phone_number: Optional[str] = Field(default=None, description="전화번호")

class AgentResponse(BaseModel):
    """에이전트 응답 형식"""
    success: bool
    agent_name: str = ""
    message: str = ""
    data: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    error: Optional[str] = None


# 사용 예시
if __name__ == "__main__":
    # 일반 유저
    normal_user = UserPersona(
        budget_level="중",
        interests=["카페", "사진"]
    )
    
    # 알레르기가 있는 유저
    allergy_user = UserPersona(
        budget_level="중",
        interests=["맛집투어"],
        allergies=["땅콩", "새우", "우유"]
    )
    
    # 다이어터 유저
    dieter_user = UserPersona(
        budget_level="중",
        interests=["카페", "다이어트"],
        is_diet_mode=True,
        diet_goal="체중감량",
        daily_calorie_goal=1500,
        daily_protein_goal=100
    )
    
    # 알레르기 + 다이어트 유저
    special_user = UserPersona(
        budget_level="고",
        interests=["힐링", "다이어트"],
        allergies=["땅콩", "밀가루"],
        is_diet_mode=True,
        diet_goal="근육증가",
        daily_calorie_goal=2200,
        daily_protein_goal=150
    )
    
    print("✅ 페르소나 스키마 생성 완료")
    print(f"다이어터 유저: {dieter_user.model_dump()}")