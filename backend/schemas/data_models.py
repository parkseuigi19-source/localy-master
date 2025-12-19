"""데이터 모델 스키마 - backend/data_models.py로 리다이렉트"""
# 실제 데이터 모델은 backend/data_models.py에 정의되어 있습니다.
from data_models import (
    PlaceData,
    AgentResponse,
    UserPersona,
    TravelState
)

# RegionInfo는 data_models.py에 없으므로 여기서 정의
from pydantic import BaseModel
from typing import Optional, List

class RegionInfo(BaseModel):
    """지역 정보 모델"""
    region_id: str
    name: str
    parent_region: Optional[str] = None
    level: int = 1  # 1: 도시, 2: 주요 지역, 3: 세부 지역
    description: Optional[str] = None
    popular_attractions: Optional[List[str]] = None
    best_season: Optional[str] = None
    travel_tips: Optional[List[str]] = None

__all__ = [
    'PlaceData',
    'AgentResponse', 
    'UserPersona',
    'TravelState',
    'RegionInfo'
]
