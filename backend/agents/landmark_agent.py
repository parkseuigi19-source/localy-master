"""슈퍼바이저 에이전트 & 랜드마크 기능 통합 (Phase 2)
중앙에서 상태(TravelState)를 관리하고 관광지 검색/상세 조회 기능을 직접 수행합니다.
"""
import os
import sys
# UTF-8 인코딩 설정 (Windows 콘솔 이모지 출력 지원)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# 부모 디렉토리 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import googlemaps
from schemas.data_models import TravelState, AgentResponse, PlaceData

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
당신은 '올인원 트래블 가이드'의 핵심 랜드마크 에이전트입니다.
사용자의 여행 코스를 위해 최고의 관광지, 테마파크, 박물관을 추천하고 상세 정보를 제공하는 것이 임무입니다.

[역할]
1. 검색 전문가: 사용자가 원하는 지역과 카테고리(테마파크, 박물관, 자연, 문화재 등)를 파악하여 정확한 장소를 찾습니다.
2. 디테일 가이드: 사용자가 관심 있어 하는 장소의 리뷰, 편의시설, 혼잡도 등을 상세히 설명합니다.
3. 문맥 파악: "거기 어때?", "첫 번째 곳 알려줘" 같은 대명사나 순서 지칭을 이전 대화 맥락(Search Results)을 통해 해석합니다.

[지침]
- 모든 대답은 한국어로 친절하고 전문적으로 작성하세요.
- 툴(Tool)을 통해 얻은 데이터에 기반해서만 답변하세요. 없는 사실을 지어내지 마세요.
- 장소 추천 시에는 평점과 핵심 특징(카테고리)을 함께 언급하세요.
- 상세 정보 제공 시, '리뷰 요약'과 '편의시설' 정보를 적극 활용하여 방문 팁을 주세요.
"""

# 사용자 정의 카테고리 매핑
TOURIST_CATEGORIES = {
    "박물관": ["박물관", "뮤지엄", "전시"],
    "미술관": ["미술관", "갤러리", "아트"],
    "테마파크": ["테마파크", "놀이공원", "월드", "랜드"],
    "아쿠아리움": ["아쿠아리움", "수족관"],
    "문화재": ["문화재", "고궁", "유적", "문화 유산", "사적"],
    "자연": ["자연", "공원", "산", "바다", "강", "호수", "숲", "해변", "계곡"],
    "야경": ["야경", "밤"],
    "실내": ["실내", "비오는", "비 오는"]
}

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# --- 랜드마크 에이전트 기능 (통합됨) ---

def search_landmarks(
    region: str,
    preference: Optional[str] = None,
    category: Optional[str] = None
) -> AgentResponse:
    """관광지 검색 전용 함수"""
    try:
        logger.info(f"🔍 관광지 검색: {region} (카테고리: {category}, 추가 선호: {preference})")
        
        # 0. Serper 웹 검색 (선택적)
        place_names_from_web = []
        if preference:
            try:
                from agents.utils.serper_utils import search_with_serper, extract_place_names
                search_query = f"{region} {preference} 관광지"
                logger.info(f"🌐 Serper 검색: {search_query}")
                serper_results = search_with_serper(search_query, num_results=10)
                if serper_results:
                    place_names_from_web = extract_place_names(serper_results, preference)
                    logger.info(f"📝 웹 검색 결과: {len(place_names_from_web)}개")
            except Exception as e:
                logger.warning(f"⚠️ Serper 검색 실패: {e}")
        
        # 1. 좌표 변환
        result = gmaps.geocode(f"{region}, 대한민국", language="ko", region="KR")
        if not result:
            return AgentResponse(
                success=False,
                agent_name="landmark",
                message=f"'{region}'을(를) 찾을 수 없습니다."
            )
            
        coords = result[0]['geometry']['location']
        
        # 2. Google Places 검색 매핑
        search_types = ['tourist_attraction'] # 기본값
        search_keyword = preference
        
        if category == '테마파크':
            search_types = ['amusement_park', 'zoo'] 
        elif category == '박물관':
            search_types = ['museum']
        elif category == '미술관':
            search_types = ['art_gallery']
        elif category == '아쿠아리움':
            search_types = ['aquarium']
        elif category == '문화재':
            search_types = ['tourist_attraction']
            if not search_keyword: search_keyword = "문화재" 
        elif category == '자연':
            search_types = ['park', 'natural_feature', 'campground']
        elif category == '야경':
            search_types = ['tourist_attraction']
            if not search_keyword: search_keyword = "야경"
        elif category == '실내':
            search_types = ['museum', 'art_gallery', 'aquarium', 'shopping_mall']
            
        all_results = {}

        for place_type in search_types:
            try:
                results = gmaps.places_nearby(
                    location=(coords['lat'], coords['lng']),
                    radius=5000,
                    type=place_type,
                    keyword=search_keyword,
                    language="ko"
                )
                
                # 결과 중복 제거 및 수집
                for place in results.get('results', []):
                    place_id = place['place_id']
                    if place_id not in all_results:
                        all_results[place_id] = place
            except Exception as type_error:
                logger.warning(f"타입 검색 실패 ({place_type}): {type_error}")
                continue

        unique_results = list(all_results.values())
        
        # 3. 필터링 (리뷰 50개 이상)
        filtered = [r for r in unique_results
                   if r.get('user_ratings_total', 0) >= 50]
        
        # 4. 정렬 (리뷰수, 평점 순)
        sorted_results = sorted(
            filtered,
            key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)),
            reverse=True
        )
        
        # 랜덤 선택 (상위 15개 중에서)
        import random
        top_candidates = sorted_results[:15]
        random.shuffle(top_candidates)
        final_candidates = top_candidates[:10]
        
        # 5. 상세 정보 로드 및 변환
        places = []
        for place in final_candidates:
            place_id = place['place_id']
            # 상세 정보 요청 (필요한 필드만)
            try:
                details_result = gmaps.place(place_id, fields=[
                    'formatted_phone_number', 'website', 
                    'opening_hours', 'formatted_address', 'photo'
                ], language="ko")
                details = details_result.get('result', {})
            except Exception as detail_error:
                logger.warning(f"상세 정보 로드 실패 ({place.get('name')}): {detail_error}")
                details = {}
            
            # 카테고리 상세 분류
            place_types = place.get('types', [])
            place_category = "관광지" # 기본값 한글화
            
            if 'amusement_park' in place_types or 'zoo' in place_types: place_category = "테마파크"
            elif 'aquarium' in place_types: place_category = "아쿠아리움"
            elif 'museum' in place_types: place_category = "박물관"
            elif 'art_gallery' in place_types: place_category = "미술관"
            elif 'park' in place_types or 'natural_feature' in place_types: place_category = "자연"
            
            # PlaceData 생성
            places.append(PlaceData(
                place_id=place_id,
                name=place['name'],
                category=place_category,
                address=details.get('formatted_address', place.get('vicinity', '')),
                latitude=place['geometry']['location']['lat'],
                longitude=place['geometry']['location']['lng'],
                region=region,
                rating=place.get('rating', 0.0),
                review_count=place.get('user_ratings_total', 0),
                price_level=place.get('price_level', 0),
                opening_hours=details.get('opening_hours', {}).get('weekday_text', []),
                open_now=details.get('opening_hours', {}).get('open_now'),
                phone=details.get('formatted_phone_number'),
                website=details.get('website'),
                google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            ))
        
        return AgentResponse(
            success=True,
            agent_name="landmark",
            data=[p.model_dump() for p in places],
            count=len(places),
            message=f"{region} 관광지 {len(places)}곳을 찾았습니다!"
        )
        
    except Exception as e:
        logger.error(f"❌ 검색 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="landmark",
            message="검색 중 오류가 발생했습니다.",
            error=str(e)
        )

def get_landmark_detail(place_id: str) -> AgentResponse:
    """특정 장소의 상세 정보를 조회합니다."""
    try:
        if not gmaps:
            raise Exception("Google Maps API Key가 설정되지 않았습니다.")
            
        logger.info(f"🔍 장소 상세 상세 조회: {place_id}")
        
        # 상세 정보 요청
        # fields docs: https://developers.google.com/maps/documentation/places/web-service/details#fields
        try:
            details_result = gmaps.place(place_id, fields=[
                'name', 'formatted_address', 'geometry', 'rating', 'user_ratings_total',
                'formatted_phone_number', 'website', 'opening_hours', 
                'price_level', 'type', 'editorial_summary', 'reviews', 
                'wheelchair_accessible_entrance'  # 편의시설 예시
            ], language="ko")
        except Exception as api_error:
            # 혹시 type/types 문제 등이 생기면 기본 필드로 재시도
            logger.warning(f"상세 조회 1차 시도 실패(필드 문제 가능성), 기본 필드로 재시도: {api_error}")
            details_result = gmaps.place(place_id, language="ko")
        
        place = details_result.get('result', {})
        if not place:
             return AgentResponse(
                success=False,
                agent_name="landmark",
                message="장소 정보를 가져올 수 없습니다."
            )

        # 카테고리 분류
        place_types = place.get('types', [])
        category = "관광지"
        if 'amusement_park' in place_types or 'zoo' in place_types: category = "테마파크"
        elif 'aquarium' in place_types: category = "아쿠아리움"
        elif 'museum' in place_types: category = "박물관"
        elif 'art_gallery' in place_types: category = "미술관"
        elif 'park' in place_types or 'natural_feature' in place_types: category = "자연"

        # 리뷰 추출 (최대 5개)
        reviews = [r.get('text', '') for r in place.get('reviews', [])[:5] if r.get('text')]
        
        # 편의시설 & 접근성 추론 (Types 및 필드 기반)
        amenities = []
        accessibility = []
        
        # 접근성 확인
        if 'wheelchair_accessible_entrance' in place:
            if place['wheelchair_accessible_entrance']:
                accessibility.append("휠체어 입구 이용 가능")
            else:
                accessibility.append("휠체어 입구 이용 어려움")
        
        # 편의시설 확인
        if 'parking' in place_types: amenities.append("주차장")
        if 'rest_room' in place_types: amenities.append("화장실")
        if 'restaurant' in place_types or 'cafe' in place_types: amenities.append("식음료 시설")
        if 'store' in place_types or 'shopping_mall' in place_types: amenities.append("기념품샵/상점")
            
        # 입장료 정보 (Price Level 기반 추정)
        ticket_info = "정보 없음"
        price_level = place.get('price_level')
        if price_level is not None:
            if price_level == 0:
                ticket_info = "무료 입장 가능성 높음"
            elif price_level == 1:
                ticket_info = "저렴 (약 1만원 이하)"
            elif price_level == 2:
                ticket_info = "보통 (약 1~3만원)"
            elif price_level >= 3:
                ticket_info = "다소 비쌈 (3만원 이상)"
        elif place.get('business_status') == 'OPERATIONAL':
             # price_level이 없지만 운영 중이면 유료일 수 있음 (카테고리 따라 다름)
             if category in ['박물관', '미술관', '테마파크', '아쿠아리움']:
                 ticket_info = "유료 (현장 확인 필요)"
        
        # 혼잡도 정보 추출 (리뷰 기반 분석)
        crowdedness_info = "정보 없음"
        crowded_keywords = {
            '매우 혼잡': ['사람이 너무 많', '엄청 붐', '발 디딜 틈', '인산인해', '줄이 너무', '대기 시간이 길'],
            '혼잡': ['사람 많', '붐비', '혼잡', '줄 서', '대기'],
            '보통': ['적당', '보통', '괜찮'],
            '한산': ['한산', '여유', '사람 적', '조용']
        }
        
        crowdedness_mentions = []
        for level, keywords in crowded_keywords.items():
            for review in reviews:
                if any(keyword in review for keyword in keywords):
                    crowdedness_mentions.append(level)
                    break
        
        if crowdedness_mentions:
            # 가장 많이 언급된 혼잡도 수준 선택
            from collections import Counter
            most_common = Counter(crowdedness_mentions).most_common(1)[0][0]
            crowdedness_info = f"{most_common} (리뷰 기반)"
            
            # 추가 팁 제공
            if most_common in ['매우 혼잡', '혼잡']:
                crowdedness_info += " - 평일 오전이나 비성수기 방문 권장"
            elif most_common == '한산':
                crowdedness_info += " - 여유롭게 관람 가능"
        else:
            # 리뷰 수 기반 추정
            review_count = place.get('user_ratings_total', 0)
            if review_count > 10000:
                crowdedness_info = "인기 명소 (혼잡 예상) - 사전 예약 권장"
            elif review_count > 5000:
                crowdedness_info = "보통 혼잡도 예상"
            elif review_count > 1000:
                crowdedness_info = "적당한 방문객 수 예상"
            else:
                crowdedness_info = "비교적 한산할 것으로 예상"
        
        # 가이드 투어 정보 추출 (리뷰 기반 + 카테고리별 일반 정보)
        guide_tours = []
        
        # 리뷰에서 가이드 투어 언급 확인
        tour_keywords = ['가이드', '투어', '해설', '도슨트', '안내']
        has_tour_mention = any(
            any(keyword in review for keyword in tour_keywords)
            for review in reviews
        )
        
        # 카테고리별 가이드 투어 정보 제공
        if category == '박물관':
            guide_tours.append({
                'name': '도슨트 해설 투어',
                'description': '전문 도슨트가 주요 전시물을 설명해주는 무료/유료 해설 프로그램',
                'price': '무료 또는 별도 요금',
                'note': '현장 문의 또는 홈페이지 예약 필요'
            })
        elif category == '미술관':
            guide_tours.append({
                'name': '큐레이터 투어',
                'description': '큐레이터가 작품의 배경과 의미를 설명하는 전문 투어',
                'price': '무료 또는 별도 요금',
                'note': '정기 운영 시간 확인 필요'
            })
        elif category == '테마파크':
            guide_tours.append({
                'name': '가이드 투어 프로그램',
                'description': '주요 시설과 어트랙션을 효율적으로 둘러보는 가이드 투어',
                'price': '입장권 별도 또는 포함',
                'note': '사전 예약 권장'
            })
        elif category == '문화재':
            guide_tours.append({
                'name': '문화재 해설사 투어',
                'description': '문화재 해설사가 역사와 문화적 가치를 설명하는 무료 해설',
                'price': '무료',
                'note': '정기 운영 시간 확인 필요'
            })
        elif category == '자연':
            guide_tours.append({
                'name': '생태 해설 프로그램',
                'description': '자연환경 해설사가 동식물과 생태계를 설명하는 프로그램',
                'price': '무료',
                'note': '계절별 운영 시간 상이'
            })
        
        # 리뷰에서 투어 언급이 있으면 추가 정보 제공
        if has_tour_mention and not guide_tours:
            guide_tours.append({
                'name': '가이드 투어',
                'description': '방문객 리뷰에서 가이드 투어가 언급되었습니다',
                'price': '현장 문의',
                'note': '자세한 정보는 전화 또는 웹사이트 확인'
            })
                 
        # PlaceData 생성
        place_data = PlaceData(
            place_id=place_id,
            name=place.get('name', ''),
            category=category,
            address=place.get('formatted_address', ''),
            latitude=place['geometry']['location']['lat'],
            longitude=place['geometry']['location']['lng'],
            region="", 
            rating=place.get('rating', 0.0),
            review_count=place.get('user_ratings_total', 0),
            price_level=place.get('price_level', 0),
            opening_hours=place.get('opening_hours', {}).get('weekday_text', []),
            open_now=place.get('opening_hours', {}).get('open_now'),
            phone=place.get('formatted_phone_number'),
            website=place.get('website'),
            google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{place_id}",
            
            # 상세 필드
            editorial_summary=place.get('editorial_summary', {}).get('overview'),
            recent_reviews=reviews,
            amenities=amenities,
            accessibility=accessibility,
            ticket_info=ticket_info,
            crowdedness_info=crowdedness_info, 
            best_time_to_visit="영업시간 참고",
            guide_tours=guide_tours 
        )

        return AgentResponse(
            success=True,
            agent_name="landmark_detail",
            data=[place_data.model_dump()],
            count=1,
            message=f"{place_data.name} 상세 정보를 가져왔습니다."
        )

    except Exception as e:
        logger.error(f"❌ 상세 정보 조회 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="landmark",
            message="상세 정보 조회 중 오류가 발생했습니다.",
            error=str(e)
        )



def find_nearby_landmarks(
    place_id: str,
    radius: int = 2000,
    limit: int = 5
) -> AgentResponse:
    """특정 관광지 주변의 다른 관광지를 찾습니다.
    
    Args:
        place_id: 기준 장소의 place_id
        radius: 검색 반경 (미터, 기본 2km)
        limit: 최대 결과 개수
    
    Returns:
        AgentResponse with nearby places
    """
    try:
        if not gmaps:
            raise Exception("Google Maps API Key가 설정되지 않았습니다.")
        
        logger.info(f"📍 주변 관광지 검색: {place_id} (반경 {radius}m)")
        
        # 기준 장소 정보 가져오기
        base_place = gmaps.place(place_id, fields=['name', 'geometry'], language="ko")
        base_name = base_place.get('result', {}).get('name', '기준 장소')
        base_location = base_place.get('result', {}).get('geometry', {}).get('location', {})
        
        if not base_location:
            return AgentResponse(
                success=False,
                agent_name="nearby",
                message="기준 장소를 찾을 수 없습니다."
            )
        
        # 주변 관광지 검색
        nearby_results = gmaps.places_nearby(
            location=(base_location['lat'], base_location['lng']),
            radius=radius,
            type='tourist_attraction',
            language="ko"
        )
        
        # 기준 장소 제외 및 필터링
        filtered_results = [
            r for r in nearby_results.get('results', [])
            if r['place_id'] != place_id and r.get('user_ratings_total', 0) >= 50
        ]
        
        # 거리 계산 및 정렬
        import math
        def calculate_distance(lat1, lon1, lat2, lon2):
            """두 좌표 간 거리 계산 (미터)"""
            R = 6371000  # 지구 반경 (미터)
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            
            a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c
        
        for result in filtered_results:
            loc = result['geometry']['location']
            distance = calculate_distance(
                base_location['lat'], base_location['lng'],
                loc['lat'], loc['lng']
            )
            result['distance_meters'] = distance
        
        # 거리순 정렬 및 제한
        sorted_results = sorted(filtered_results, key=lambda x: x['distance_meters'])[:limit]
        
        # PlaceData 형식으로 변환
        places = []
        for place in sorted_results:
            # 상세 정보 가져오기
            try:
                details_result = gmaps.place(place['place_id'], fields=[
                    'formatted_phone_number', 'website', 
                    'opening_hours', 'formatted_address'
                ], language="ko")
                details = details_result.get('result', {})
            except:
                details = {}
            
            distance_km = place['distance_meters'] / 1000
            distance_text = f"{distance_km:.1f}km" if distance_km >= 1 else f"{int(place['distance_meters'])}m"
            
            places.append(PlaceData(
                place_id=place['place_id'],
                name=place['name'],
                category="관광지",
                address=details.get('formatted_address', place.get('vicinity', '')),
                latitude=place['geometry']['location']['lat'],
                longitude=place['geometry']['location']['lng'],
                region="",
                rating=place.get('rating', 0.0),
                review_count=place.get('user_ratings_total', 0),
                price_level=place.get('price_level', 0),
                opening_hours=details.get('opening_hours', {}).get('weekday_text', []),
                open_now=details.get('opening_hours', {}).get('open_now'),
                phone=details.get('formatted_phone_number'),
                website=details.get('website'),
                google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}",
                description=f"{base_name}에서 {distance_text} 거리"
            ))
        
        return AgentResponse(
            success=True,
            agent_name="nearby",
            data=[p.model_dump() for p in places],
            count=len(places),
            message=f"{base_name} 주변 {len(places)}곳을 찾았습니다."
        )
        
    except Exception as e:
        logger.error(f"❌ 주변 관광지 검색 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="nearby",
            message="주변 관광지 검색 중 오류가 발생했습니다.",
            error=str(e)
        )

def recommend_by_season(
    region: str,
    season: str
) -> AgentResponse:
    """계절에 맞는 관광지를 추천합니다.
    
    Args:
        region: 지역
        season: 계절 (봄, 여름, 가을, 겨울)
    
    Returns:
        AgentResponse with recommended places
    """
    try:
        logger.info(f"🌸 계절 기반 추천: {region} - {season}")
        
        # 계절에 따른 카테고리 및 키워드 선택
        category = None
        preference = None
        message_prefix = ""
        
        if season in ["봄", "spring"]:
            category = "자연"
            preference = "벚꽃"
            message_prefix = f"🌸 {season} 추천! 벚꽃/꽃 명소"
        elif season in ["여름", "summer"]:
            category = "자연"
            preference = "해수욕장"
            message_prefix = f"🌊 {season} 추천! 해변/워터파크"
        elif season in ["가을", "fall", "autumn"]:
            category = "자연"
            preference = "단풍"
            message_prefix = f"🍂 {season} 추천! 단풍/등산 명소"
        elif season in ["겨울", "winter"]:
            category = "실내"
            preference = "스키"
            message_prefix = f"❄️ {season} 추천! 실내/스키 관광지"
        else:
            # 기본값: 전체 검색
            category = None
            preference = None
            message_prefix = f"🌈 {season} 관광지"
        
        # 기존 search_landmarks 함수 활용
        result = search_landmarks(region, preference=preference, category=category)
        
        if result.success:
            result.message = f"{message_prefix} {result.count}곳을 찾았습니다."
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 계절 기반 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="season_recommend",
            message="계절 기반 추천 중 오류가 발생했습니다.",
            error=str(e)
        )

def recommend_by_time(
    region: str,
    time_of_day: str
) -> AgentResponse:
    """시간대에 맞는 관광지를 추천합니다.
    
    Args:
        region: 지역
        time_of_day: 시간대 (아침, 오후, 저녁, 밤)
    
    Returns:
        AgentResponse with recommended places
    """
    try:
        logger.info(f"🕐 시간대 기반 추천: {region} - {time_of_day}")
        
        # 시간대에 따른 카테고리 및 키워드 선택
        category = None
        preference = None
        message_prefix = ""
        
        if time_of_day in ["아침", "morning"]:
            category = "자연"
            preference = "일출"
            message_prefix = f"🌅 {time_of_day} 추천! 일출/산책 명소"
        elif time_of_day in ["오후", "afternoon", "점심"]:
            category = None  # 전체 카테고리
            preference = None
            message_prefix = f"☀️ {time_of_day} 추천! 다양한 관광지"
        elif time_of_day in ["저녁", "evening"]:
            category = "야경"
            preference = "석양"
            message_prefix = f"🌆 {time_of_day} 추천! 야경/석양 명소"
        elif time_of_day in ["밤", "night"]:
            category = "야경"
            preference = "야시장"
            message_prefix = f"🌃 {time_of_day} 추천! 야경/야시장"
        else:
            # 기본값: 전체 검색
            category = None
            preference = None
            message_prefix = f"🌈 {time_of_day} 관광지"
        
        # 기존 search_landmarks 함수 활용
        result = search_landmarks(region, preference=preference, category=category)
        
        if result.success:
            result.message = f"{message_prefix} {result.count}곳을 찾았습니다."
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 시간대 기반 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="time_recommend",
            message="시간대 기반 추천 중 오류가 발생했습니다.",
            error=str(e)
        )

# --- 슈퍼바이저 기능 ---

class SupervisorAgent:
    def __init__(self, user_id: str = "default_user"):
        self.state = TravelState(user_id=user_id)
        logger.info(f"🤖 슈퍼바이저 에이전트 초기화 (User ID: {user_id})")

    def handle_request(self, user_input: str) -> str:
        """
        사용자 입력을 분석하여 적절한 기능을 수행하고 상태를 업데이트합니다.
        (Phase 2: 간단한 키워드/규칙 기반 라우팅)
        """
        logger.info(f"🗣️ 사용자 요청 수신: {user_input}")
        
        # 1. 의도 파악 (간이 로직)
        if "테마파크" in user_input or "박물관" in user_input or "관광지" in user_input or "찾아줘" in user_input:
            return self._handle_search(user_input)
        elif "상세" in user_input or "자세히" in user_input or "첫번째" in user_input:
            return self._handle_detail(user_input)
        else:
            return "죄송합니다. 관광지 검색이나 상세 정보 조회만 현재 지원됩니다."

    def _handle_search(self, user_input: str) -> str:
        """관광지 검색 처리 및 상태 저장"""
        # 파라미터 추출
        region = "서울" 
        if "제주" in user_input: region = "제주"
        elif "부산" in user_input: region = "부산"
        elif "용인" in user_input: region = "용인"
        elif "경주" in user_input: region = "경주"
        elif "강릉" in user_input: region = "강릉"
        
        category = None
        for cat, keywords in TOURIST_CATEGORIES.items():
            if any(k in user_input for k in keywords):
                category = cat
                break
        
        # 내부 함수 호출
        response = search_landmarks(region, category=category)
        
        if response.success:
            # 상태 업데이트 (공유 메모리)
            self.state.search_results[region] = [
                PlaceData(**p) for p in response.data
            ]
            self.state.current_region = region
            
            # 응답 생성
            items_str = "\n".join([f"- {i+1}. {p['name']} ({p['category']})" for i, p in enumerate(response.data[:5])])
            return f"[{region}] 검색 결과입니다:\n{items_str}\n\n이 중 궁금한 곳이 있나요?"
        else:
            return f"검색 실패: {response.message}"

    def _handle_detail(self, user_input: str) -> str:
        """상세 정보 처리 (상태 기반 Context 사용)"""
        # 문맥 확인
        if not self.state.current_region or not self.state.search_results.get(self.state.current_region):
            return "이전 검색 기록이 없습니다. 먼저 관광지를 검색해주세요."
            
        # 대상 장소 식별
        target_index = 0  # 기본값: 첫 번째 결과
        if "두번째" in user_input or "2번" in user_input: target_index = 1
        elif "세번째" in user_input or "3번" in user_input: target_index = 2
        
        recent_results = self.state.search_results[self.state.current_region]
        if target_index >= len(recent_results):
            return "해당 번호의 장소를 찾을 수 없습니다."
            
        target_place = recent_results[target_index]
        place_id = target_place.place_id
        
        # 내부 함수 호출
        detail_response = get_landmark_detail(place_id)
        
        if detail_response.success:
            detail_data = detail_response.data[0]
            # 상태에 상세 정보 병합/업데이트 (선택된 장소로 격상)
            updated_place = PlaceData(**detail_data)
            if "selected" not in self.state.selected_places:
                self.state.selected_places["selected"] = []
            self.state.selected_places["selected"].append(updated_place)
    
            # 응답 구성
            info = []
            info.append(f"🏢 {updated_place.name}")
            
            # 1. 평점, 리뷰
            info.append(f"⭐ 평점: {updated_place.rating} / 5.0 (리뷰 {updated_place.review_count:,}개)")
            
            # 2. 주소
            info.append(f"📍 주소: {updated_place.address}")
            
            # 3. 전화
            if updated_place.phone:
                info.append(f"📞 전화: {updated_place.phone}")
            else:
                info.append(f"📞 전화: 정보 없음")
                
            # 4. 영업중
            if updated_place.open_now is True:
                info.append(f"🟢 영업중: 현재 영업중입니다.")
            elif updated_place.open_now is False:
                info.append(f"🔴 영업중: 현재 영업 종료입니다.")
            else:
                 info.append(f"⚪ 영업중: 정보 없음")

            # 5. 영업시간
            if updated_place.opening_hours:
                hours_str = "\n".join([f"   {h}" for h in updated_place.opening_hours])
                info.append(f"🕒 영업시간:\n{hours_str}")
            else:
                info.append(f"🕒 영업시간: 정보 없음")
            
            # 6. 가이드 투어
            if updated_place.guide_tours:
                info.append(f"\n🎯 가이드 투어 정보:")
                for tour in updated_place.guide_tours:
                    tour_info = []
                    tour_info.append(f"   • {tour.get('name', '가이드 투어')}")
                    if tour.get('description'):
                        tour_info.append(f"     - 설명: {tour['description']}")
                    if tour.get('price'):
                        tour_info.append(f"     - 가격: {tour['price']}")
                    if tour.get('note'):
                        tour_info.append(f"     - 참고: {tour['note']}")
                    info.append("\n".join(tour_info))
            
            # 7. 지도연동
            info.append(f"\n🗺️ 지도연동: {updated_place.google_maps_url}")
            
            return "\n".join(info)
        else:
            return f"상세 정보 조회 실패: {detail_response.message}"

# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🏛️ 관광지 추천 에이전트 테스트")
    print("=" * 60)
    
    if not GOOGLE_API_KEY:
        print("\n❌ Google API 키가 설정되지 않았습니다!")
        print("📝 .env 파일에 GOOGLE_PLACES_API_KEY를 추가하세요.\n")
        exit(1)
    
    # 테스트 케이스
    test_cases = [
        ("서울", "미술관,박물관", 5),
        ("부산", "테마파크", 3),
        ("경주", "문화재", 5),
        ("강릉", "자연", 5),
    ]
    
    for region, category, num in test_cases:
        print(f"\n📍 {region} - {category} 관광지 검색 (상위 {num}개):")
        print("-" * 60)
        
        result = search_landmarks(region, category=category)
        
        if result.success and result.count > 0:
            print(f"✅ 성공! {result.count}개 발견\n")
            # 요청한 개수만큼만 출력
            for i, place in enumerate(result.data[:num], 1):
                print(f"{i}. {place['name']}")
                print(f"   ⭐ 평점: {place['rating']} ({place['review_count']}개 리뷰)")
                print(f"   📍 {place['address']}")
                print(f"   🔗 {place['google_maps_url']}")
                if place.get('phone'):
                    print(f"   📞 {place['phone']}")
                if place.get('opening_hours'):
                    print(f"   🕐 영업시간: {place['opening_hours'][0] if place['opening_hours'] else '정보 없음'}")
                print()
        else:
            print(f"❌ {result.message}\n")
    
    # 카테고리 없이 검색
    print(f"\n📍 제주 - 전체 관광지 검색 (상위 5개):")
    print("-" * 60)
    result = search_landmarks("제주", category=None)
    if result.success:
        print(f"✅ {result.count}개 발견!")
        for i, place in enumerate(result.data[:5], 1):
            print(f"{i}. {place['name']} - ⭐{place['rating']} ({place['review_count']}개 리뷰)")
