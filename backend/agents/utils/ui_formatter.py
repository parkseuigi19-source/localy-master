"""
UI 요소 생성 유틸리티 함수들
"""
from typing import List, Dict, Any, Optional


def create_place_list_ui(
    places: List[Dict[str, Any]],
    title: str = "추천 장소",
    selection_mode: str = "single"
) -> Dict[str, Any]:
    """
    장소 목록 UI 요소 생성
    
    Args:
        places: 장소 정보 리스트 [{"name": str, "address": str, "lat": float, "lng": float, "tags": list, "google_maps_url": str}]
        title: UI 제목
        selection_mode: 선택 모드 ("single" 또는 "multiple")
    
    Returns:
        UI 요소 딕셔너리
    """
    return {
        "type": "place_list",
        "data": {
            "title": title,
            "places": places,
            "selection_mode": selection_mode
        }
    }


def create_calendar_ui(
    mode: str = "range",
    min_date: Optional[str] = None,
    max_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    달력 UI 요소 생성
    
    Args:
        mode: 선택 모드 ("single" 또는 "range")
        min_date: 최소 날짜 (YYYY-MM-DD)
        max_date: 최대 날짜 (YYYY-MM-DD)
    
    Returns:
        UI 요소 딕셔너리
    """
    return {
        "type": "calendar",
        "data": {
            "mode": mode,
            "min_date": min_date,
            "max_date": max_date
        }
    }
