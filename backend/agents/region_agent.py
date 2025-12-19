"""지역 추천 에이전트 - LLM 기반 동적 검색"""
import logging
import json
import os
from typing import List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import googlemaps
from schemas.data_models import RegionInfo, AgentResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API 클라이언트 초기화
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=OPENAI_API_KEY
) if OPENAI_API_KEY else None

gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None


# 인기 도시 하드코딩 데이터 (즉시 응답)
POPULAR_DESTINATIONS = [
    {
        "name": "제주도",
        "description": "한국 최고의 관광지, 아름다운 자연과 해변",
        "tags": ["자연", "해변", "힐링", "드라이브", "UNESCO"],
        "popularity": 10,
        "best_for": ["신혼여행", "가족여행", "힐링"]
    },
    {
        "name": "부산",
        "description": "해운대 해변과 감천문화마을로 유명한 항구도시",
        "tags": ["해변", "도시", "맛집", "야경", "문화"],
        "popularity": 9,
        "best_for": ["맛집투어", "해변여행", "도시여행"]
    },
    {
        "name": "강릉",
        "description": "동해안의 아름다운 해변과 커피거리",
        "tags": ["해변", "카페", "자연", "힐링", "일출"],
        "popularity": 8,
        "best_for": ["힐링", "카페투어", "해변여행"]
    },
    {
        "name": "경주",
        "description": "신라 천년의 역사가 살아있는 문화유산 도시",
        "tags": ["역사", "문화", "UNESCO", "전통", "유적"],
        "popularity": 8,
        "best_for": ["문화체험", "역사탐방", "교육여행"]
    },
    {
        "name": "전주",
        "description": "한옥마을과 비빔밥으로 유명한 전통 도시",
        "tags": ["한옥", "맛집", "전통", "문화", "음식"],
        "popularity": 7,
        "best_for": ["맛집투어", "문화체험", "전통체험"]
    }
]

POPULAR_CITIES = {
    "서울": [
        {"name": "명동", "description": "쇼핑과 먹거리의 중심, 외국인 관광객 밀집 지역", "tags": ["쇼핑", "먹거리", "관광", "화장품", "번화가"]},
        {"name": "강남", "description": "서울 최대 번화가, 고급 쇼핑과 나이트라이프", "tags": ["쇼핑", "번화가", "나이트라이프", "고급", "K-POP"]},
        {"name": "홍대", "description": "젊음의 거리, 클럽과 라이브 음악, 예술의 중심", "tags": ["클럽", "음악", "예술", "젊음", "카페"]},
        {"name": "북촌", "description": "한옥마을과 전통 문화, 서울의 역사", "tags": ["한옥", "전통", "역사", "사진", "문화"]},
        {"name": "이태원", "description": "다국적 문화와 이색 맛집, 세계 음식의 거리", "tags": ["다국적", "맛집", "이색", "문화", "나이트라이프"]},
    ],
    "부산": [
        {"name": "해운대", "description": "해변과 마린시티, 고급 호텔과 레스토랑이 밀집한 관광 중심지", "tags": ["해변", "마린시티", "야경", "호텔", "맛집"]},
        {"name": "광안리", "description": "광안대교 야경과 카페거리, 젊은 분위기의 해변", "tags": ["해변", "광안대교", "야경", "카페", "회센터"]},
        {"name": "남포동", "description": "자갈치시장과 국제시장, 부산의 전통 먹거리 중심지", "tags": ["시장", "먹거리", "자갈치", "쇼핑", "전통"]},
        {"name": "서면", "description": "부산 최대 번화가, 쇼핑과 맛집의 중심", "tags": ["쇼핑", "번화가", "맛집", "카페", "나이트라이프"]},
        {"name": "송도", "description": "한국 최초 해수욕장, 송도 스카이워크와 케이블카", "tags": ["해변", "케이블카", "스카이워크", "가족여행", "산책"]},
    ],
    "제주": [
        {"name": "제주시", "description": "제주 공항 인근, 동문시장과 제주항 주변", "tags": ["공항", "시장", "중심가", "숙소", "쇼핑"]},
        {"name": "서귀포", "description": "남부 해안 도시, 천지연 폭포와 정방폭포", "tags": ["폭포", "해안", "자연", "관광", "맛집"]},
        {"name": "성산", "description": "성산일출봉과 섭지코지, 일출 명소", "tags": ["일출봉", "일출", "자연", "UNESCO", "드라마촬영지"]},
        {"name": "중문", "description": "중문관광단지, 고급 리조트와 테디베어 박물관", "tags": ["리조트", "관광", "박물관", "해변", "가족여행"]},
        {"name": "애월", "description": "카페거리와 해안도로, 감성적인 서부 해안", "tags": ["카페", "해안도로", "일몰", "감성", "사진"]},
    ],
    "강릉": [
        {"name": "경포대", "description": "경포호와 경포해변, 넓은 백사장과 소나무 숲", "tags": ["해변", "경포호", "자연", "산책", "일출"]},
        {"name": "안목해변", "description": "커피 거리로 유명한 해변, 강릉 커피의 성지", "tags": ["커피", "카페", "해변", "일출", "로스터리"]},
        {"name": "주문진", "description": "항구와 해산물 시장, 신선한 회와 대게", "tags": ["항구", "해산물", "시장", "회", "대게"]},
        {"name": "강릉역 주변", "description": "강릉 중심가, 교통의 요지이자 숙소 밀집 지역", "tags": ["중심가", "숙소", "교통", "쇼핑", "맛집"]},
        {"name": "정동진", "description": "일출 명소, 모래시계 공원과 해안 철길", "tags": ["일출", "해안철길", "관광", "사진", "드라마"]},
    ],
    "인천": [
        {"name": "차이나타운", "description": "한국 최대 차이나타운, 중화요리와 이국적 분위기", "tags": ["중화요리", "관광", "이색체험", "사진", "맛집"]},
        {"name": "송도", "description": "송도 센트럴파크, 현대적 해양 공원과 수상택시", "tags": ["공원", "야경", "데이트", "산책", "현대적"]},
        {"name": "월미도", "description": "놀이공원과 해안 산책로, 가족 나들이 명소", "tags": ["놀이공원", "해안", "가족여행", "산책", "맛집"]},
        {"name": "영종도", "description": "인천공항과 을왕리 해수욕장, 해산물 맛집", "tags": ["공항", "해변", "해산물", "일몰", "카페"]},
    ],
    "전주": [
        {"name": "전주 한옥마을", "description": "전통 한옥과 전주 비빔밥, 한국 전통의 중심", "tags": ["한옥", "전통", "비빔밥", "맛집", "문화"]},
        {"name": "객사길", "description": "전주의 중심가, 쇼핑과 먹거리", "tags": ["쇼핑", "먹거리", "중심가", "카페", "전통"]},
        {"name": "덕진공원", "description": "연꽃과 호수, 전주의 대표 공원", "tags": ["공원", "연꽃", "산책", "자연", "사진"]},
    ],
}


def recommend_regions(
    destination: str,
    travel_style: Optional[str] = None,  # "힐링", "액티비티", "맛집투어", "문화체험"
    season: Optional[str] = None  # "봄", "여름", "가을", "겨울"
) -> AgentResponse:
    """
    LLM을 사용하여 동적으로 지역 추천 (고도화)
    
    Args:
        destination: 목적지 (예: "부산", "강릉")
        travel_style: 여행 스타일
        season: 계절
    
    Returns:
        AgentResponse: 추천 지역 리스트
    """
    try:
        logger.info(f"🗺️ 지역 추천 시작: {destination}")
        
        # 1. 인기 도시 확인 (즉시 응답)
        if destination in POPULAR_CITIES:
            logger.info(f"⚡ 인기 도시 - 즉시 응답!")
            regions_data = POPULAR_CITIES[destination]
            
            # parent_region 및 Google Maps URL 추가
            regions = []
            for region in regions_data:
                # Google Maps 검색 URL 생성
                search_query = f"{destination} {region['name']}".replace(" ", "+")
                maps_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
                
                region_dict = {
                    "name": region["name"],
                    "description": region["description"],
                    "tags": region["tags"],
                    "parent_region": destination,
                    "google_maps_url": maps_url
                }
                regions.append(region_dict)
            
            return AgentResponse(
                success=True,
                agent_name="region_recommender",
                data=regions,
                count=len(regions),
                message=f"{destination} 추천 지역 {len(regions)}개 찾음! 🎯"
            )
        
        # 2. LLM 사용 (1-2초 소요)
        if not llm:
            return AgentResponse(
                success=False,
                agent_name="region_recommender",
                data=[],
                count=0,
                message="OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.",
                error="OPENAI_API_KEY not found"
            )
        
        logger.info(f"🤖 LLM으로 검색 중... (1-2초 소요)")
        
        # 여행 스타일 및 계절 필터
        style_text = f"\n여행 스타일: {travel_style}" if travel_style else ""
        season_text = f"\n계절: {season}" if season else ""
        
        # LLM 프롬프트
        prompt = f"""당신은 한국 여행 전문가입니다. {destination}의 주요 세부 지역(동/구/읍/면 단위)을 5-7개 추천해주세요.{style_text}{season_text}

각 지역마다 다음 정보를 제공해주세요:
- name: 지역 이름 (간단명료하게)
- description: 해당 지역의 특징 설명 (50자 이내)
- tags: 지역 특징을 나타내는 태그 5개

반드시 아래 JSON 형식으로만 응답하세요:
{{
    "regions": [
        {{
            "name": "지역명",
            "description": "설명",
            "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
        }}
    ]
}}

JSON만 출력하고 다른 설명은 추가하지 마세요."""

        # LLM 호출
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # JSON 파싱
        try:
            # 코드 블록 제거 (```json ... ``` 형식)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            data = json.loads(response_text)
            regions_data = data.get("regions", [])
            
            if not regions_data:
                return AgentResponse(
                    success=False,
                    agent_name="region_recommender",
                    data=[],
                    count=0,
                    message=f"'{destination}'에 대한 지역 정보를 생성하지 못했습니다.",
                    error="Empty regions list from LLM"
                )
            
            # RegionInfo 형식으로 변환 및 Google Maps URL 추가
            regions = []
            for region in regions_data:
                # Google Maps 검색 URL 생성
                search_query = f"{destination} {region.get('name', '')}".replace(" ", "+")
                maps_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
                
                region_dict = {
                    "name": region.get("name", ""),
                    "description": region.get("description", ""),
                    "tags": region.get("tags", []),
                    "parent_region": destination,
                    "google_maps_url": maps_url
                }
                regions.append(region_dict)
            
            logger.info(f"✅ {destination} 지역 {len(regions)}개 생성!")
            
            return AgentResponse(
                success=True,
                agent_name="region_recommender",
                data=regions,
                count=len(regions),
                message=f"{destination} 추천 지역 {len(regions)}개 찾음! 🎯"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            logger.error(f"응답 내용: {response_text[:200]}")
            return AgentResponse(
                success=False,
                agent_name="region_recommender",
                data=[],
                count=0,
                message="LLM 응답 파싱 중 오류 발생",
                error=f"JSON decode error: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"❌ 지역 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="region_recommender",
            data=[],
            count=0,
            message="지역 추천 중 오류 발생",
            error=str(e)
        )


def get_popular_destinations(travel_style: Optional[str] = None, top_n: int = 5) -> AgentResponse:
    """
    한국의 인기 여행지 추천
    
    Args:
        travel_style: 여행 스타일 ("힐링", "맛집투어", "문화체험" 등)
        top_n: 추천할 여행지 개수
    
    Returns:
        AgentResponse: 인기 여행지 리스트
    """
    try:
        logger.info(f"🌟 인기 여행지 추천 시작")
        
        destinations = POPULAR_DESTINATIONS.copy()
        
        # 여행 스타일 필터링
        if travel_style:
            filtered = []
            for dest in destinations:
                if travel_style in dest.get('best_for', []):
                    filtered.append(dest)
            
            if filtered:
                destinations = filtered
        
        # 인기도 순 정렬
        destinations.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        # 상위 N개 선택
        top_destinations = destinations[:top_n]
        
        # Google Maps URL 추가
        results = []
        for dest in top_destinations:
            search_query = dest['name'].replace(" ", "+")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
            
            dest_dict = {
                "name": dest["name"],
                "description": dest["description"],
                "tags": dest["tags"],
                "popularity": dest["popularity"],
                "best_for": dest["best_for"],
                "google_maps_url": maps_url
            }
            results.append(dest_dict)
        
        logger.info(f"✅ 인기 여행지 {len(results)}개 추천!")
        
        return AgentResponse(
            success=True,
            agent_name="popular_destinations",
            data=results,
            count=len(results),
            message=f"한국 인기 여행지 {len(results)}개 추천! 🌟"
        )
        
    except Exception as e:
        logger.error(f"❌ 인기 여행지 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="popular_destinations",
            data=[],
            count=0,
            message="인기 여행지 추천 중 오류 발생",
            error=str(e)
        )


def get_region_attractions(
    region: str,
    category: Optional[str] = None,  # "자연", "문화", "쇼핑", "음식"
    sort_by: str = "rating",  # "rating", "review_count", "distance"
    weather: Optional[str] = None,  # "비", "더움", "추움", "맑음"
    num_results: int = 10
) -> AgentResponse:
    """
    특정 지역의 관광지, 명소, 액티비티 검색 (고도화)
    
    Args:
        region: 지역명
        category: 카테고리 필터
        sort_by: 정렬 기준
        weather: 날씨 조건
        num_results: 결과 개수
    
    Returns:
        AgentResponse: 관광지 리스트
    """
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="region_attractions",
                data=[],
                count=0,
                message="Google API 키가 설정되지 않았습니다.",
                error="GOOGLE_PLACES_API_KEY not found"
            )
        
        logger.info(f"🎯 명소 검색: {region}")
        
        # 1. 좌표 변환
        geocode_result = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode_result:
            return AgentResponse(
                success=False,
                agent_name="region_attractions",
                data=[],
                count=0,
                message=f"'{region}' 지역을 찾을 수 없습니다.",
                error=f"Geocoding failed for region: {region}"
            )
        
        coords = geocode_result[0]['geometry']['location']
        
        # 카테고리별 키워드
        category_keywords = {
            "자연": "자연 공원 해변 산 바다",
            "문화": "박물관 미술관 전통 역사",
            "쇼핑": "시장 쇼핑 백화점 거리",
            "음식": "맛집 식당 카페 음식"
        }
        
        keyword = category_keywords.get(category, "") if category else ""
        
        # 날씨별 키워드
        weather_keywords = {
            "비": "실내 박물관 미술관 쇼핑몰 카페 영화관",
            "더움": "해변 워터파크 수영장 에어컨 실내",
            "추움": "찜질방 온천 실내 따뜻한",
            "맑음": "공원 산책 야외 자연"
        }
        
        weather_keyword = weather_keywords.get(weather, "") if weather else ""
        
        # 키워드 결합
        combined_keyword = f"{keyword} {weather_keyword}".strip()
        
        # 2. Google Places 검색 (관광지)
        search_params = {
            'location': (coords['lat'], coords['lng']),
            'radius': 5000,
            'type': 'tourist_attraction',
            'language': 'ko'
        }
        
        if combined_keyword:
            search_params['keyword'] = combined_keyword
        
        results = gmaps.places_nearby(**search_params)
        
        if not results.get('results'):
            return AgentResponse(
                success=True,
                agent_name="region_attractions",
                data=[],
                count=0,
                message=f"{region}에서 명소를 찾지 못했습니다."
            )
        
        # 3. 필터링 및 정렬 (리뷰 30개 이상)
        filtered = [
            r for r in results['results']
            if r.get('user_ratings_total', 0) >= 30
        ]
        
        if not filtered:
            filtered = results['results']  # 필터 완화
        
        sorted_results = sorted(
            filtered,
            key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)),
            reverse=True
        )[:num_results]
        
        # 4. 데이터 변환
        attractions = []
        for place in sorted_results:
            search_query = f"{region} {place['name']}".replace(" ", "+")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
            
            attractions.append({
                "name": place['name'],
                "address": place.get('vicinity', ''),
                "rating": place.get('rating', 0),
                "review_count": place.get('user_ratings_total', 0),
                "types": place.get('types', []),
                "google_maps_url": maps_url
            })
        
        logger.info(f"✅ 명소 {len(attractions)}개 찾음!")
        
        return AgentResponse(
            success=True,
            agent_name="region_attractions",
            data=attractions,
            count=len(attractions),
            message=f"{region} 명소 {len(attractions)}개 찾음! 🎯"
        )
        
    except Exception as e:
        logger.error(f"❌ 명소 검색 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="region_attractions",
            data=[],
            count=0,
            message="명소 검색 중 오류 발생",
            error=str(e)
        )


def get_region_best_time(region: str, season: Optional[str] = None) -> AgentResponse:
    """
    LLM을 사용하여 지역 방문 최적 시간 추천
    
    Args:
        region: 지역명 (예: "강릉 경포대", "부산 해운대")
        season: 계절 (선택, 예: "여름", "겨울", "봄", "가을")
    
    Returns:
        AgentResponse: 최적 방문 시간 추천
    """
    try:
        if not llm:
            return AgentResponse(
                success=False,
                agent_name="region_best_time",
                data=[],
                count=0,
                message="OpenAI API 키가 설정되지 않았습니다.",
                error="OPENAI_API_KEY not found"
            )
        
        logger.info(f"⏰ 최적 시간 추천: {region}")
        
        # LLM 프롬프트
        season_text = f", 특히 {season}에" if season else ""
        prompt = f"""당신은 한국 여행 전문가입니다. {region}을(를) 방문하기 가장 좋은 시간을 추천해주세요{season_text}.

다음 정보를 JSON 형식으로 제공:
- best_time_of_day: 하루 중 최적 시간대 (예: "일출 시간(새벽 5-6시)", "오전 10-12시")
- best_season: 최적 계절 (예: "봄(3-5월)", "여름(6-8월)")
- reason: 추천 이유 (100자 이내)
- avoid_time: 피해야 할 시간 (예: "주말 오후", "여름 성수기")
- special_events: 특별 이벤트나 축제 (있다면)

반드시 아래 JSON 형식으로만 응답하세요:
{{
    "best_time_of_day": "시간대",
    "best_season": "계절",
    "reason": "이유",
    "avoid_time": "피해야 할 시간",
    "special_events": "특별 이벤트 (없으면 빈 문자열)"
}}

JSON만 출력하고 다른 설명은 추가하지 마세요."""

        # LLM 호출
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # JSON 파싱
        try:
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            data = json.loads(response_text)
            
            logger.info(f"✅ 최적 시간 추천 완료!")
            
            return AgentResponse(
                success=True,
                agent_name="region_best_time",
                data=[data],
                count=1,
                message=f"{region} 최적 방문 시간 추천 완료! 🎯"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            return AgentResponse(
                success=False,
                agent_name="region_best_time",
                data=[],
                count=0,
                message="LLM 응답 파싱 중 오류 발생",
                error=f"JSON decode error: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"❌ 최적 시간 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="region_best_time",
            data=[],
            count=0,
            message="최적 시간 추천 중 오류 발생",
            error=str(e)
        )


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🗺️ 지역 추천 에이전트 테스트 (LLM 기반)")
    print("=" * 60)
    
    if not OPENAI_API_KEY:
        print("\n❌ OpenAI API 키가 설정되지 않았습니다!")
        print("📝 .env 파일에 OPENAI_API_KEY를 추가하세요.\n")
        exit(1)
    
    test_destinations = ["부산", "강릉", "인천", "속초"]
    
    for dest in test_destinations:
        print(f"\n📍 {dest} 지역 추천:")
        result = recommend_regions(dest)
        
        if result.success:
            print(f"✅ 성공! {result.count}개 지역 발견\n")
            for i, region in enumerate(result.data, 1):
                print(f"{i}. {region['name']}")
                print(f"   📝 {region['description']}")
                print(f"   🏷️ {', '.join(region['tags'])}\n")
        else:
            print(f"❌ 실패: {result.message}\n")
