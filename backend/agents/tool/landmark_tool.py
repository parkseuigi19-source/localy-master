"""LangChain 툴 템플릿"""
from langchain.tools import tool

@tool #1. 장소검색
def search_places_tool(region: str, category: str, preference: str = None) -> dict:
    """
    장소 검색 툴
    
    Args:
        region: 검색 지역
        category: 박물관 | 미술관 | 테마파크 | 아쿠아리움 | 문화재 | 자연 | 야경 | 실내
        preference: 선호도
    """
    from agents.landmark_agent import search_landmarks, TOURIST_CATEGORIES
    
    # 지원하는 카테고리 목록
    supported_categories = list(TOURIST_CATEGORIES.keys())
    
    target_category = None
    if category in supported_categories:
        target_category = category
        
    result = search_landmarks(region, preference, category=target_category)
    return result.model_dump()

@tool #2. 장소상세정보
def get_landmark_detail_tool(place_id: str) -> dict:
    """
    특정 관광지의 상세 정보를 조회합니다.
    
    [반환 데이터 포함 항목]
    - 기본정보: 이름, 주소, 전화번호, 웹사이트, 설명
    - 운영정보: 영업시간, 현재 영업 여부
    - 입장정보: 티켓 가격/무료 여부 (ticket_info)
    - 편의시설: 주차, 화장실, 식음료 등 (amenities)
    - 접근성: 휠체어 이용 가능 여부 (accessibility)
    - 추가정보: 리뷰 요약, 평점
    - 가이드 투어 정보 (이름, 설명, 가격, 예약 링크등)
    - 혼잡도 정보
    
    검색 결과의 'place_id'를 입력으로 사용해야 합니다.
    """
    from agents.landmark_agent import get_landmark_detail
    result = get_landmark_detail(place_id)
    return result.model_dump()

@tool #3. 주변관광지
def find_nearby_landmarks_tool(
    place_id: str,
    radius: int = 2000,
    limit: int = 5
) -> dict:
    """
    특정 관광지 주변의 다른 관광지를 찾습니다.
    
    Args:
        place_id: 기준 장소의 place_id (검색 결과에서 얻은 place_id)
        radius: 검색 반경 (미터 단위, 기본 2000m = 2km)
        limit: 최대 결과 개수 (기본 5개)
    
    Returns:
        주변 관광지 리스트 (거리순 정렬)
        - 각 장소의 기본 정보 (이름, 평점, 주소 등)
        - description 필드에 기준 장소로부터의 거리 포함
    
    활용 예시: "경복궁 근처에 다른 볼거리 있나요?"
    """
    from agents.landmark_agent import find_nearby_landmarks
    result = find_nearby_landmarks(place_id, radius, limit)
    return result.model_dump()

@tool #4. 계절별추천
def recommend_by_season_tool(
    region: str,
    season: str
) -> dict:
    """
    계절에 맞는 관광지를 추천합니다.
    
    Args:
        region: 검색 지역
        season: 계절 (봄, 여름, 가을, 겨울)
    
    Returns:
        계절에 맞는 관광지 리스트
        - 봄 → 벚꽃/꽃 명소, 공원
        - 여름 → 해변, 워터파크, 계곡
        - 가을 → 단풍 명소, 산, 공원
        - 겨울 → 실내 관광지, 스키장
    
    활용 예시: "제주도 봄에 가면 좋은 곳 추천해줘"
    """
    from agents.landmark_agent import recommend_by_season
    result = recommend_by_season(region, season)
    return result.model_dump()

@tool #5. 시간대별추천
def recommend_by_time_tool(
    region: str,
    time_of_day: str
) -> dict:
    """
    시간대에 맞는 관광지를 추천합니다.
    
    Args:
        region: 검색 지역
        time_of_day: 시간대 (아침, 오후, 저녁, 밤)
    
    Returns:
        시간대에 맞는 관광지 리스트
        - 아침 → 일출 명소, 공원, 산책로
        - 오후 → 박물관, 테마파크, 다양한 관광지
        - 저녁 → 야경 명소, 석양 명소
        - 밤 → 야경, 야시장
    
    활용 예시: "부산 저녁에 갈만한 곳 추천해줘"
    """
    from agents.landmark_agent import recommend_by_time
    result = recommend_by_time(region, time_of_day)
    return result.model_dump()
