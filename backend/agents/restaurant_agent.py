"""맛집 추천 에이전트 (간소화 - 핵심 기능만)"""
import os
import logging
import json
from typing import List, Optional
from dotenv import load_dotenv
import googlemaps
from langchain_openai import ChatOpenAI
from schemas.data_models import PlaceData, AgentResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API 클라이언트 초기화
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=OPENAI_API_KEY
) if OPENAI_API_KEY else None

# API 호출 캐시 (성능 최적화)
_place_cache = {}

# LLM 결과 캐시 (성능 최적화 - 3-5초 → 0.1초)
_llm_cache = {}


def get_place_details(place_id: str, fields: list) -> dict:
    """
    Google Places API 호출 with 캐싱
    
    Args:
        place_id: Place ID
        fields: 필요한 필드 리스트
    
    Returns:
        dict: Place details
    """
    # 캐시 키 생성
    cache_key = f"{place_id}:{','.join(sorted(fields))}"
    
    # 캐시에 있으면 반환
    if cache_key in _place_cache:
        return _place_cache[cache_key]
    
    # API 호출
    try:
        result = gmaps.place(place_id, fields=fields, language='ko')['result']
        _place_cache[cache_key] = result
        return result
    except Exception as e:
        logger.warning(f"API 호출 실패: {e}")
        return {}


def detect_region_type(region: str) -> tuple[str, int]:
    """
    지역 타입을 감지하고 적절한 검색 반경 반환
    
    Args:
        region: 지역명
    
    Returns:
        (타입, 반경) 튜플
    """
    if ' ' in region.strip():
        return ("district", 10000)
    else:
        return ("city", 15000)


def search_restaurants(
    region: str,
    preference: Optional[str] = None,
    age_group: Optional[str] = None,
    gender: Optional[str] = None,
    companion: Optional[str] = None,
    occasion: Optional[str] = None,
    dietary_restrictions: Optional[List[str]] = None,
    sort_by: str = "review_count",
    num_results: int = 10,
    radius: Optional[int] = None
) -> AgentResponse:
    """
    맛집 검색 (고도화)
    
    맞춤 추천:
    - 성별/나이/동행자/상황별 추천
    - preference: 음식 종류 ("한식", "일식", "비건", "채식")
    - dietary_restrictions: 제외할 음식 (알레르기 등)
    
    Args:
        region: 검색 지역
        preference: 음식 선호
        age_group: 연령대
        gender: 성별
        companion: 동행자
        occasion: 상황
        dietary_restrictions: 제외 음식
        sort_by: 정렬
        num_results: 결과 개수
        radius: 반경
    
    Returns:
        AgentResponse: 맛집 리스트
    """
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="restaurant",
                data=[],
                count=0,
                message="Google API 키가 설정되지 않았습니다.",
                error="GOOGLE_PLACES_API_KEY not found"
            )
        
        logger.info(f"🔍 맛집 검색: {region}")
        
        # 0. Serper로 먼저 웹 검색 (유명한 가게 이름 추출)
        place_names_from_web = []
        try:
            from agents.utils.serper_utils import search_with_serper, extract_place_names
            
            # 1차: 메뉴 특화 검색 (사용자 입력 그대로)
            if preference:
                search_query_specific = f"{region} {preference} 맛집"
                logger.info(f"🌐 Serper 1차 검색 (메뉴 특화): {search_query_specific}")
                serper_results = search_with_serper(search_query_specific, num_results=10)
                
                if serper_results:
                    place_names_from_web = extract_place_names(serper_results, preference)
                    logger.info(f"📝 1차 검색 결과: {len(place_names_from_web)}개")
                
                # 2차: 일반 검색 (결과가 부족하면)
                if len(place_names_from_web) < 5:
                    # 메뉴에서 카테고리 추출 (예: "토마토 파스타" → "파스타")
                    general_category = preference.split()[-1] if ' ' in preference else preference
                    
                    if general_category != preference:  # 메뉴 특화와 다른 경우만
                        search_query_general = f"{region} {general_category} 맛집"
                        logger.info(f"🌐 Serper 2차 검색 (일반): {search_query_general}")
                        serper_results_2 = search_with_serper(search_query_general, num_results=10)
                        
                        if serper_results_2:
                            additional_names = extract_place_names(serper_results_2, general_category)
                            # 중복 제거하고 추가
                            for name in additional_names:
                                if name not in place_names_from_web:
                                    place_names_from_web.append(name)
                            logger.info(f"📝 2차 검색 추가: {len(additional_names)}개 (총 {len(place_names_from_web)}개)")
        except Exception as e:
            logger.warning(f"⚠️ Serper 검색 실패 (Google Places만 사용): {e}")
        
        # 1. 좌표 변환
        geocode_result = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode_result:
            return AgentResponse(
                success=False,
                agent_name="restaurant",
                data=[],
                count=0,
                message=f"'{region}' 지역을 찾을 수 없습니다.",
                error=f"Geocoding failed for region: {region}"
            )
        
        coords = geocode_result[0]['geometry']['location']
        logger.info(f"📍 좌표: {coords['lat']}, {coords['lng']}")
        
        # 지역 타입 감지 및 반경 결정
        if radius is None:
            region_type, auto_radius = detect_region_type(region)
            search_radius = auto_radius
            type_text = "도시 전체" if region_type == "city" else "세부 지역"
            logger.info(f"🎯 검색 타입: {type_text} (반경 {search_radius}m)")
        else:
            search_radius = radius
            logger.info(f"🎯 수동 반경: {search_radius}m")
        
        # 2. Google Places 검색 (20개만)
        search_params = {
            'location': (coords['lat'], coords['lng']),
            'radius': search_radius,
            'type': 'restaurant',
            'language': 'ko'
        }
        
        if preference:
            search_params['keyword'] = preference
        
        all_results = []
        results = gmaps.places_nearby(**search_params)
        all_results.extend(results.get('results', []))
        
        logger.info(f"📊 총 검색 결과: {len(all_results)}개")
        
        if not all_results:
            return AgentResponse(
                success=True,
                agent_name="restaurant",
                data=[],
                count=0,
                message=f"{region}에서 맛집을 찾지 못했습니다. 검색 조건을 변경해보세요."
            )
        
        # 3. 호텔/숙박시설 제외
        filtered_restaurants = [
            r for r in all_results
            if not any(t in r.get('types', []) for t in ['lodging', 'hotel', 'motel', 'hostel', 'resort'])
        ]
        
        logger.info(f"📊 호텔 제외: {len(all_results)}개 → {len(filtered_restaurants)}개")
        
        # 4. 리뷰 필터링 (리뷰 50개 이상)
        filtered = [
            r for r in filtered_restaurants
            if r.get('user_ratings_total', 0) >= 50
        ]
        
        logger.info(f"📊 필터링: {len(filtered_restaurants)}개 → {len(filtered)}개 (리뷰 50개 이상)")
        
        # 필터링 결과가 없으면 리뷰 10개 이상으로 완화
        if not filtered:
            filtered = [
                r for r in filtered_restaurants
                if r.get('user_ratings_total', 0) >= 10
            ]
            logger.info(f"📊 필터 완화: {len(filtered)}개 (리뷰 10개 이상)")
        
        # 5. 정렬
        if sort_by == "rating":
            sorted_results = sorted(
                filtered,
                key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)),
                reverse=True
            )[:num_results]
        elif sort_by == "popularity":
            sorted_results = sorted(
                filtered,
                key=lambda x: (x.get('user_ratings_total', 0) * x.get('rating', 0)),
                reverse=True
            )[:num_results]
        else:  # review_count (기본)
            sorted_results = sorted(
            filtered,
            key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)),
            reverse=True
        )
        
        # 다양성을 위한 랜덤 셔플 (상위 15개 중에서)
        import random
        top_candidates = sorted_results[:15]  # 상위 15개
        random.shuffle(top_candidates)  # 랜덤 섞기
        final_results = top_candidates[:num_results]  # num_results 개 선택
        
        logger.info(f"🎯 랜덤 선택: {len(final_results)}개")
        
        # 6. 상세 정보 로드
        places = []
        for place in final_results:
            place_id = place['place_id']
            
            # 상세 정보 가져오기
            try:
                details = gmaps.place(
                    place_id,
                    fields=[
                        'formatted_phone_number',
                        'website',
                        'opening_hours',
                        'formatted_address',
                        'photo',
                        'price_level'
                    ],
                    language='ko'
                )['result']
            except Exception as e:
                logger.warning(f"⚠️ 상세 정보 로드 실패 ({place['name']}): {e}")
                details = {}
            
            # 사진 URL 생성
            photo_urls = []
            if details.get('photos'):
                for photo in details['photos'][:3]:
                    photo_ref = photo.get('photo_reference')
                    if photo_ref:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={GOOGLE_API_KEY}"
                        photo_urls.append(photo_url)
            
            place_data = PlaceData(
                place_id=place_id,
                name=place['name'],
                category='restaurant',
                address=details.get('formatted_address', place.get('vicinity', '')),
                latitude=place['geometry']['location']['lat'],
                longitude=place['geometry']['location']['lng'],
                region=region,
                rating=place.get('rating', 0),
                review_count=place.get('user_ratings_total', 0),
                price_level=details.get('price_level', 0),
                opening_hours=details.get('opening_hours', {}).get('weekday_text', []),
                open_now=details.get('opening_hours', {}).get('open_now'),
                phone=details.get('formatted_phone_number'),
                website=details.get('website'),
                images=photo_urls,
                google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                tags=[preference] if preference else []
            )
            
            places.append(place_data)
        
        logger.info(f"✅ 맛집 {len(places)}개 찾음!")
        
        return AgentResponse(
            success=True,
            agent_name="restaurant",
            data=[p.dict() for p in places],
            count=len(places),
            message=f"{region} 맛집 {len(places)}개 찾음! 🎯"
        )
        
    except Exception as e:
        logger.error(f"❌ 맛집 검색 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="restaurant",
            data=[],
            count=0,
            message="맛집 검색 중 오류 발생",
            error=str(e)
        )


def get_restaurant_reviews(place_id: str, num_reviews: int = 10) -> AgentResponse:
    """
    특정 맛집의 리뷰를 LLM으로 요약
    
    Args:
        place_id: Google Place ID
        num_reviews: 요약할 리뷰 개수
    
    Returns:
        AgentResponse: 리뷰 요약
    """
    # LLM 캐시 확인
    cache_key = f"reviews:{place_id}:{num_reviews}"
    if cache_key in _llm_cache:
        logger.info(f"⚡ 캐시 hit! 리뷰 요약 즉시 반환")
        return _llm_cache[cache_key]
    
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="restaurant_reviews",
                data=[],
                count=0,
                message="Google API 키가 설정되지 않았습니다.",
                error="GOOGLE_PLACES_API_KEY not found"
            )
        
        if not llm:
            return AgentResponse(
                success=False,
                agent_name="restaurant_reviews",
                data=[],
                count=0,
                message="OpenAI API 키가 설정되지 않았습니다.",
                error="OPENAI_API_KEY not found"
            )
        
        logger.info(f"📝 리뷰 요약: {place_id}")
        
        # Google Places에서 리뷰 가져오기
        details = gmaps.place(place_id, fields=['name', 'reviews'], language='ko')
        place_name = details['result'].get('name', '알 수 없는 장소')
        reviews = details['result'].get('reviews', [])[:num_reviews]
        
        if not reviews:
            return AgentResponse(
                success=True,
                agent_name="restaurant_reviews",
                data=[],
                count=0,
                message=f"{place_name}의 리뷰를 찾을 수 없습니다."
            )
        
        # 리뷰 텍스트 추출
        review_texts = [r.get('text', '') for r in reviews if r.get('text')]
        combined_reviews = "\n\n".join(review_texts[:10])
        
        # LLM으로 요약
        prompt = f"""다음은 "{place_name}" 맛집의 실제 고객 리뷰입니다. 이 리뷰들을 분석하여 요약해주세요.

리뷰:
{combined_reviews}

다음 형식의 JSON으로 응답하세요:
{{
    "summary": "전체 요약 (3-5줄)",
    "pros": ["장점1", "장점2", "장점3"],
    "cons": ["단점1", "단점2"],
    "recommended_menu": ["추천 메뉴1", "추천 메뉴2"],
    "atmosphere": "분위기 설명",
    "service": "서비스 평가"
}}

JSON만 출력하고 다른 설명은 추가하지 마세요."""

        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # JSON 파싱
        try:
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            summary_data = json.loads(response_text)
            summary_data['place_name'] = place_name
            summary_data['review_count'] = len(reviews)
            
            logger.info(f"✅ 리뷰 요약 완료!")
            
            result = AgentResponse(
                success=True,
                agent_name="restaurant_reviews",
                data=[summary_data],
                count=1,
                message=f"{place_name} 리뷰 요약 완료! 🎯"
            )
            
            # 캐시에 저장
            _llm_cache[cache_key] = result
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            return AgentResponse(
                success=False,
                agent_name="restaurant_reviews",
                data=[],
                count=0,
                message="리뷰 요약 파싱 중 오류 발생",
                error=f"JSON decode error: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"❌ 리뷰 요약 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="restaurant_reviews",
            data=[],
            count=0,
            message="리뷰 요약 중 오류 발생",
            error=str(e)
        )


def extract_menu(place_id: str, num_reviews: int = 20) -> AgentResponse:
    """
    리뷰에서 메뉴 추출 및 추천 (LLM 기반)
    
    Args:
        place_id: Google Place ID
        num_reviews: 분석할 리뷰 개수
    
    Returns:
        AgentResponse: 추천 메뉴 리스트
    """
    # LLM 캐시 확인
    cache_key = f"menu:{place_id}:{num_reviews}"
    if cache_key in _llm_cache:
        logger.info(f"⚡ 캐시 hit! 메뉴 추출 즉시 반환")
        return _llm_cache[cache_key]
    
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="menu_extraction",
                data=[],
                count=0,
                message="Google API 키가 설정되지 않았습니다.",
                error="GOOGLE_PLACES_API_KEY not found"
            )
        
        if not llm:
            return AgentResponse(
                success=False,
                agent_name="menu_extraction",
                data=[],
                count=0,
                message="OpenAI API 키가 설정되지 않았습니다.",
                error="OPENAI_API_KEY not found"
            )
        
        logger.info(f"🍽️ 메뉴 추출: {place_id}")
        
        # Google Places에서 리뷰 가져오기
        details = gmaps.place(place_id, fields=['name', 'reviews'], language='ko')
        place_name = details['result'].get('name', '알 수 없는 장소')
        reviews = details['result'].get('reviews', [])[:num_reviews]
        
        if not reviews:
            return AgentResponse(
                success=True,
                agent_name="menu_extraction",
                data=[],
                count=0,
                message=f"{place_name}의 리뷰를 찾을 수 없습니다."
            )
        
        # 리뷰 텍스트 추출
        review_texts = [r.get('text', '') for r in reviews if r.get('text')]
        combined_reviews = "\n\n".join(review_texts)
        
        # LLM으로 메뉴 추출
        prompt = f"""다음은 "{place_name}" 맛집의 실제 고객 리뷰입니다. 리뷰에서 언급된 메뉴를 추출하고 추천해주세요.

리뷰:
{combined_reviews}

다음 형식의 JSON으로 응답하세요:
{{
    "signature_menu": ["시그니처 메뉴1", "시그니처 메뉴2"],
    "popular_menu": ["인기 메뉴1", "인기 메뉴2", "인기 메뉴3"],
    "recommended_menu": ["추천 메뉴1", "추천 메뉴2"],
    "price_info": "가격대 정보 (예: 1인 15,000원~20,000원)"
}}

JSON만 출력하고 다른 설명은 추가하지 마세요."""

        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # JSON 파싱
        try:
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            menu_data = json.loads(response_text)
            menu_data['place_name'] = place_name
            menu_data['review_count'] = len(reviews)
            
            logger.info(f"✅ 메뉴 추출 완료!")
            
            result = AgentResponse(
                success=True,
                agent_name="menu_extraction",
                data=[menu_data],
                count=1,
                message=f"{place_name} 메뉴 추출 완료! 🍽️"
            )
            
            # 캐시에 저장
            _llm_cache[cache_key] = result
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            return AgentResponse(
                success=False,
                agent_name="menu_extraction",
                data=[],
                count=0,
                message="메뉴 추출 파싱 중 오류 발생",
                error=f"JSON decode error: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"❌ 메뉴 추출 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="menu_extraction",
            data=[],
            count=0,
            message="메뉴 추출 중 오류 발생",
            error=str(e)
        )


def verify_restaurant(
    place_id: str,
    user_location: Optional[tuple] = None
) -> AgentResponse:
    """
    맛집 검증 및 인기도 점수 계산
    
    6가지 요소 기반:
    1. 리뷰 수 + 평점 (40%)
    2. 최근성 (20%)
    3. 거리 (15%)
    4. 프로필 완성도 (10%)
    5. 사용자 참여도 (10%)
    6. 온라인 존재감 (5%)
    
    Args:
        place_id: Google Place ID
        user_location: 사용자 위치 (lat, lng)
    
    Returns:
        AgentResponse: 검증 결과 및 점수
    """
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="verification",
                data=[],
                count=0,
                message="Google API 키가 설정되지 않았습니다.",
                error="GOOGLE_PLACES_API_KEY not found"
            )
        
        logger.info(f"🔍 맛집 검증: {place_id}")
        
        # Google Places 상세 정보
        details = gmaps.place(
            place_id,
            fields=[
                'name', 'rating', 'user_ratings_total', 'reviews',
                'photo', 'opening_hours', 'website',
                'formatted_phone_number', 'geometry'
            ],
            language='ko'
        )['result']
        
        place_name = details.get('name', '알 수 없는 장소')
        
        # 1. 리뷰 수 + 평점 (40점)
        rating = details.get('rating', 0)
        review_count = details.get('user_ratings_total', 0)
        
        rating_score = (rating / 5.0) * 20
        review_score = min(review_count / 50, 1.0) * 20
        score_1 = rating_score + review_score
        
        # 2. 최근성 (20점)
        reviews = details.get('reviews', [])
        recent_reviews = 0
        if reviews:
            import datetime
            now = datetime.datetime.now()
            three_months_ago = now - datetime.timedelta(days=90)
            
            for review in reviews:
                review_time = review.get('time', 0)
                review_date = datetime.datetime.fromtimestamp(review_time)
                if review_date >= three_months_ago:
                    recent_reviews += 1
        
        score_2 = min(recent_reviews / 5, 1.0) * 20
        
        # 3. 거리 (15점)
        score_3 = 15  # 기본 만점
        
        # 4. 프로필 완성도 (10점)
        completeness = 0
        if details.get('photos'): completeness += 3
        if details.get('opening_hours'): completeness += 3
        if details.get('formatted_phone_number'): completeness += 2
        if details.get('website'): completeness += 2
        score_4 = completeness
        
        # 5. 사용자 참여도 (10점)
        score_5 = min(review_count / 100, 1.0) * 10
        
        # 6. 온라인 존재감 (5점)
        online_presence = 0
        if details.get('website'): online_presence += 5
        score_6 = online_presence
        
        # 총점 계산
        total_score = score_1 + score_2 + score_3 + score_4 + score_5 + score_6
        
        # 신뢰도 등급
        if total_score >= 80:
            grade = "A"
            trust_level = "매우 신뢰"
        elif total_score >= 60:
            grade = "B"
            trust_level = "신뢰"
        elif total_score >= 40:
            grade = "C"
            trust_level = "보통"
        else:
            grade = "D"
            trust_level = "주의"
        
        # 경고 메시지
        warnings = []
        if review_count < 10:
            warnings.append("리뷰가 적습니다")
        if recent_reviews < 2:
            warnings.append("최근 리뷰가 부족합니다")
        
        verification_data = {
            "place_name": place_name,
            "total_score": round(total_score, 1),
            "grade": grade,
            "trust_level": trust_level,
            "breakdown": {
                "review_rating": round(score_1, 1),
                "recency": round(score_2, 1),
                "distance": round(score_3, 1),
                "completeness": round(score_4, 1),
                "engagement": round(score_5, 1),
                "online_presence": round(score_6, 1)
            },
            "warnings": warnings,
            "stats": {
                "rating": rating,
                "review_count": review_count,
                "recent_reviews": recent_reviews
            }
        }
        
        logger.info(f"✅ 검증 완료: {total_score:.1f}점 ({grade}등급)")
        
        return AgentResponse(
            success=True,
            agent_name="verification",
            data=[verification_data],
            count=1,
            message=f"{place_name} 검증 완료! 점수: {total_score:.1f}/100 ({grade}) 🔍"
        )
        
    except Exception as e:
        logger.error(f"❌ 검증 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="verification",
            data=[],
            count=0,
            message="검증 중 오류 발생",
            error=str(e)
        )


def get_all_restaurant_info(place_id: str) -> dict:
    """
    맛집의 모든 정보를 한 번에 가져오기 (배치 처리)
    
    Returns:
        dict: {
            'reservation': {...},
            'price': {...},
            'parking': {...},
            'pet': {...}
        }
    """
    # 한 번의 API 호출로 모든 필드 가져오기
    details = get_place_details(place_id, [
        'reservable', 'reviews', 'price_level'
    ])
    
    reviews = details.get('reviews', [])
    
    # 예약 정보
    reservable = details.get('reservable', False)
    reservation_mentions = sum(1 for r in reviews[:10] if any(k in r.get('text', '').lower() for k in ['예약', 'reservation']))
    required_mentions = sum(1 for r in reviews[:10] if any(k in r.get('text', '').lower() for k in ['예약 필수', '예약해야']))
    
    reservation_info = {
        "reservation_required": required_mentions > 0 or reservable,
        "method": "전화/온라인" if reservable else "전화",
        "confidence": round(reservation_mentions / max(len(reviews[:10]), 1), 2),
        "evidence": f"{reservation_mentions}개 리뷰에서 예약 언급"
    }
    
    # 가격 정보
    price_level = details.get('price_level', 2)
    price_map = {
        0: {"average_price": 5000, "budget_level": "저렴", "recommended_budget": "1만원 이하"},
        1: {"average_price": 10000, "budget_level": "저렴", "recommended_budget": "1-2만원"},
        2: {"average_price": 20000, "budget_level": "보통", "recommended_budget": "2-3만원"},
        3: {"average_price": 35000, "budget_level": "비쌈", "recommended_budget": "3-5만원"},
        4: {"average_price": 60000, "budget_level": "고급", "recommended_budget": "5만원 이상"}
    }
    price_info = price_map.get(price_level, price_map[2])
    
    # 주차 정보
    parking_mentions = sum(1 for r in reviews[:20] if any(k in r.get('text', '').lower() for k in ['주차', 'parking']))
    free_parking = sum(1 for r in reviews[:20] if any(k in r.get('text', '').lower() for k in ['무료', '주차 편', '주차장 넓']))
    difficult_parking = sum(1 for r in reviews[:20] if any(k in r.get('text', '').lower() for k in ['주차 어려', '주차 힘', '주차 없']))
    
    if parking_mentions == 0:
        parking_info = {"available": None, "type": "정보 없음"}
    elif free_parking > difficult_parking:
        parking_info = {"available": True, "type": "무료/편리", "evidence": f"{free_parking}개 리뷰"}
    elif difficult_parking > 0:
        parking_info = {"available": False, "type": "어려움", "evidence": f"{difficult_parking}개 리뷰"}
    else:
        parking_info = {"available": True, "type": "있음", "evidence": f"{parking_mentions}개 리뷰"}
    
    # 애완견 정보
    pet_mentions = sum(1 for r in reviews[:20] if any(k in r.get('text', '').lower() for k in ['반려견', '애완견', '강아지', '펫', 'pet']))
    pet_allowed = sum(1 for r in reviews[:20] if any(k in r.get('text', '').lower() for k in ['동반 가능', '펫 프렌들리', '강아지 ok', '반려견 ok']))
    
    if pet_mentions == 0:
        pet_info = {"pet_allowed": None, "confidence": 0, "note": "정보 없음"}
    else:
        pet_info = {
            "pet_allowed": pet_allowed > 0,
            "confidence": round(pet_allowed / pet_mentions, 2) if pet_mentions > 0 else 0,
            "evidence": f"{pet_allowed}/{pet_mentions}개 리뷰에서 동반 가능 언급"
        }
    
    return {
        'reservation': reservation_info,
        'price': price_info,
        'parking': parking_info,
        'pet': pet_info
    }
