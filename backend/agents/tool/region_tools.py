"""지역 추천 관련 LangChain 툴 모음"""
from langchain.tools import tool
from typing import Optional


@tool
def recommend_regions_tool(
    destination: str,
    travel_style: Optional[str] = None,
    season: Optional[str] = None
) -> dict:
    """
    특정 도시의 추천 지역 검색 (고도화)
    
    여행 스타일과 계절에 맞는 지역을 추천합니다.
    
    Args:
        destination: 목적지 도시 (예: "부산", "서울", "제주")
        travel_style: 여행 스타일 ("힐링", "액티비티", "맛집투어", "문화체험")
        season: 계절 ("봄", "여름", "가을", "겨울")
    
    Returns:
        dict: 추천 지역 리스트
    """
    from agents.region_agent import recommend_regions
    result = recommend_regions(destination, travel_style, season)
    return result.dict()


@tool
def get_popular_destinations_tool(
    travel_style: Optional[str] = None,
    top_n: int = 5
) -> dict:
    """
    한국의 인기 여행지 추천
    
    사용자가 "어느 여행지가 유명해?" 같은 질문을 할 때 사용합니다.
    
    Args:
        travel_style: 여행 스타일 ("힐링", "맛집투어", "문화체험")
        top_n: 추천할 여행지 개수 (기본 5개)
    
    Returns:
        dict: 인기 여행지 리스트
    """
    from agents.region_agent import get_popular_destinations
    result = get_popular_destinations(travel_style, top_n)
    return result.dict()


@tool
def get_region_attractions_tool(
    region: str,
    category: Optional[str] = None,
    sort_by: str = "rating",
    weather: Optional[str] = None,
    num_results: int = 10
) -> dict:
    """
    특정 지역의 관광지, 명소 검색 (고도화)
    
    날씨에 맞는 장소를 추천합니다.
    
    Args:
        region: 지역명 (예: "부산 해운대", "강릉 경포대")
        category: 카테고리 ("자연", "문화", "쇼핑", "음식")
        sort_by: 정렬 기준 ("rating", "review_count", "distance")
        weather: 날씨 ("비", "더움", "추움", "맑음")
        num_results: 결과 개수 (기본 10개)
    
    Returns:
        dict: 관광지 리스트
    """
    from agents.region_agent import get_region_attractions
    result = get_region_attractions(region, category, sort_by, weather, num_results)
    return result.dict()


@tool
def get_region_best_time_tool(region: str, season: Optional[str] = None) -> dict:
    """
    특정 지역을 방문하기 가장 좋은 시간을 추천합니다.
    
    LLM을 사용하여 해당 지역의 특성을 고려한 최적 방문 시간을 추천합니다.
    
    Args:
        region: 지역명 (예: "강릉 경포대", "부산 해운대")
        season: 계절 (선택, 예: "여름", "겨울", "봄", "가을")
    
    Returns:
        dict: 최적 방문 시간 추천
    """
    from agents.region_agent import get_region_best_time
    result = get_region_best_time(region, season)
    return result.dict()
