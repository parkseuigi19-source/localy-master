"""숙소 검색 툴 모음 - 4개 툴 + 병렬 처리 최적화

Tools:
1. search_accommodations: 숙소 검색 (고급 필터링)
2. summarize_reviews: AI 리뷰 요약
3. compare_booking_prices: 실시간 가격 비교 (병렬 처리!)
4. get_recommended_accommodations: AI 맞춤 추천

✨ 최적화:
- 가격 비교 3개 플랫폼 병렬 처리 (3배 빠름!)
- 5분 캐싱으로 중복 요청 즉시 응답
"""
import os
import logging
import asyncio
import requests
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import googlemaps
from openai import OpenAI
from langchain.tools import tool
from schemas.data_models import PlaceData, AgentResponse

load_dotenv()
logger = logging.getLogger(__name__)

# httpx HTTP 로그 숨기기 (깔끔한 출력)
logging.getLogger("httpx").setLevel(logging.WARNING)

# API 클라이언트
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# 캐시 & 타임아웃 설정
_price_cache = {}
CACHE_TTL = 300  # 5분
QUICK_TIMEOUT = 10
NORMAL_TIMEOUT = 20
MAX_TIMEOUT = 30


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_reviews_enhanced(place_id: str) -> list:
    """New Places API로 리뷰 최대한 수집 (실패 시 기존 API로 폴백)"""
    # 1차 시도: New Places API
    try:
        logger.info("  🔍 New API로 리뷰 수집 시도...")
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            "X-Goog-FieldMask": "reviews"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            new_api_reviews = data.get('reviews', [])
            
            if new_api_reviews:
                converted_reviews = []
                for review in new_api_reviews:
                    converted = {
                        'text': review.get('text', {}).get('text', '') if isinstance(review.get('text'), dict) else review.get('text', ''),
                        'rating': review.get('rating', 0),
                        'author_name': review.get('authorAttribution', {}).get('displayName', '익명') if isinstance(review.get('authorAttribution'), dict) else review.get('author_name', '익명'),
                        'relative_time_description': review.get('relativePublishTimeDescription', '') or review.get('relative_time_description', ''),
                        'time': review.get('publishTime', 0) or review.get('time', 0)
                    }
                    converted_reviews.append(converted)
                logger.info(f"  ✅ New API 성공: {len(converted_reviews)}개 리뷰 수집!")
                return converted_reviews
    except Exception as e:
        logger.warning(f"  ⚠️ New API 실패: {e}")
    
    # 2차 시도: 기존 Places API
    logger.info("  🔄 기존 API로 폴백...")
    try:
        if not gmaps:
            return []
        details = gmaps.place(place_id, fields=['reviews'], language='ko')
        reviews = details.get('result', {}).get('reviews', [])
        logger.info(f"  ✅ 기존 API: {len(reviews)}개 리뷰 수집")
        return reviews
    except Exception as e:
        logger.error(f"  ❌ 기존 API도 실패: {e}")
        return []


# ============================================================================
# ASYNC HELPERS FOR PARALLEL PRICE COMPARISON
# ============================================================================

async def _fetch_booking_price_async(place_name: str, check_in: str, check_out: str, num_guests: int, nights: int) -> Optional[Dict]:
    """Booking.com 가격 조회 (비동기)"""
    try:
        logger.info("  📊 Booking.com 조회 중...")
        
        async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
            # Step 1: 호텔 검색
            search_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
            }
            
            # Rate limit 대응 재시도
            max_retries = 2
            response = None
            for attempt in range(max_retries):
                response = await client.get(search_url, headers=headers, params={"query": place_name})
                
                if response.status_code == 429 and attempt < max_retries - 1:
                    logger.warning(f"    ⚠️ Booking.com Rate Limit, 재시도 {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(2)
                    continue
                break
            
            if not response or response.status_code != 200:
                logger.warning(f"    ⚠️ Booking.com search failed: {response.status_code if response else 'No response'}")
                return None
            
            data = response.json()
            hotel_dest_id = None
            
            if data.get('data'):
                for item in data['data']:
                    if item.get('dest_type') == 'hotel':
                        hotel_dest_id = item.get('dest_id')
                        break
            
            if not hotel_dest_id:
                logger.warning("    ⚠️ Booking.com: Hotel not found")
                return None
            
            # Step 2: 가격 조회
            price_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
            price_params = {
                "dest_id": hotel_dest_id,
                "search_type": "hotel",
                "arrival_date": check_in,
                "departure_date": check_out,
                "adults": str(num_guests),
                "room_qty": "1",
                "languagecode": "ko-kr",
                "currency_code": "KRW"
            }
            
            price_response = await client.get(price_url, headers=headers, params=price_params)
            
            if price_response.status_code == 200:
                price_data = price_response.json()
                hotels = price_data.get('data', {}).get('hotels', [])
                
                if hotels:
                    hotel = hotels[0]
                    price = hotel.get('price', {}).get('grossPrice', {}).get('amount', 0)
                    
                    if price > 0:
                        per_night_price = price / nights if nights > 0 else price
                        logger.info(f"    ✅ Booking.com: {int(per_night_price):,}원")
                        return {
                            'platform': 'Booking.com',
                            'price': int(per_night_price),
                            'currency': 'KRW',
                            'hotel_name': hotel.get('name', place_name),
                            'room_type': '스탠다드',
                            'rating': hotel.get('rating', 0)
                        }
        
        return None
    except Exception as e:
        logger.warning(f"    ⚠️ Booking.com error: {e}")
        return None


async def _fetch_agoda_price_async(place_name: str, check_in: str, check_out: str, nights: int) -> Optional[Dict]:
    """Agoda 가격 조회 (비동기)"""
    try:
        logger.info("  📊 Agoda 조회 중...")
        
        async with httpx.AsyncClient(timeout=NORMAL_TIMEOUT) as client:
            url = "https://agoda-travel.p.rapidapi.com/agoda-app/hotels/search-overnight"
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "agoda-travel.p.rapidapi.com"
            }
            params = {
                "query": place_name,
                "checkin": check_in,
                "checkout": check_out
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # 응답 구조 파싱
                hotels = []
                if data.get('data'):
                    data_content = data['data']
                    if isinstance(data_content, list):
                        hotels = data_content
                    elif isinstance(data_content, dict):
                        hotels = data_content.get('properties', []) or data_content.get('hotels', [])
                elif isinstance(data, list):
                    hotels = data
                
                if hotels:
                    # 호텔 이름 매칭
                    for hotel in hotels[:20]:
                        content = hotel.get('content', {})
                        hotel_name = ''
                        if content.get('informationSummary'):
                            info = content['informationSummary']
                            hotel_name = info.get('defaultName', '') or info.get('localeName', '')
                        if not hotel_name:
                            hotel_name = content.get('name', '') or hotel.get('name', '')
                        
                        # 한글/영문 매칭
                        place_clean = place_name.replace(" ", "").replace("-", "").lower()
                        hotel_clean = hotel_name.replace(" ", "").replace("-", "").lower()
                        
                        korean_to_english = {'롯데': 'lotte', '호텔': 'hotel', '서울': 'seoul'}
                        place_english = place_clean
                        for kr, en in korean_to_english.items():
                            place_english = place_english.replace(kr, en)
                        
                        if (place_clean in hotel_clean or hotel_clean in place_clean or
                            place_english in hotel_clean or hotel_clean in place_english):
                            
                            # 가격 추출
                            price = 0
                            currency = 'KRW'
                            pricing = hotel.get('pricing', {})
                            if pricing.get('offers') and isinstance(pricing['offers'], list) and pricing['offers']:
                                offer = pricing['offers'][0]
                                if offer.get('roomOffers') and isinstance(offer['roomOffers'], list) and offer['roomOffers']:
                                    room_offer = offer['roomOffers'][0]
                                    if room_offer.get('room'):
                                        room = room_offer['room']
                                        if isinstance(room.get('pricing'), list) and room['pricing']:
                                            room_pricing = room['pricing'][0]
                                            currency = room_pricing.get('currency', 'KRW')
                                            if room_pricing.get('price'):
                                                price_obj = room_pricing['price']
                                                if isinstance(price_obj, dict):
                                                    price = (price_obj.get('perRoomPerNight', {}).get('exclusive', {}).get('display') or
                                                            price_obj.get('perNight', {}).get('exclusive', {}).get('display') or 0)
                            
                            # USD → KRW 변환
                            if currency == 'USD' and price > 0:
                                price = price * 1300
                            
                            if price > 0:
                                logger.info(f"    ✅ Agoda: {int(price):,}원")
                                return {
                                    'platform': 'Agoda',
                                    'price': int(price),
                                    'currency': 'KRW',
                                    'hotel_name': hotel_name,
                                    'room_type': '스탠다드',
                                    'rating': round(hotel.get('rating', 0) or hotel.get('starRating', 0), 1)
                                }
        
        logger.warning(f"    ⚠️ Agoda: '{place_name}' 호텔을 찾을 수 없음")
        return None
    except Exception as e:
        logger.warning(f"    ⚠️ Agoda error: {e}")
        return None


async def _fetch_airbnb_price_async(place_name: str, check_in: str, check_out: str, num_guests: int, nights: int) -> Optional[Dict]:
    """Airbnb 가격 조회 (비동기)"""
    try:
        logger.info("  📊 Airbnb 조회 중...")
        
        async with httpx.AsyncClient(timeout=NORMAL_TIMEOUT) as client:
            url = "https://airbnb13.p.rapidapi.com/search-location"
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "airbnb13.p.rapidapi.com"
            }
            params = {
                "location": place_name,
                "checkin": check_in,
                "checkout": check_out,
                "adults": str(num_guests),
                "children": "0"
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # 응답 구조 파싱
                listings = []
                if data.get('results'):
                    listings = data['results']
                elif data.get('data'):
                    if isinstance(data['data'], list):
                        listings = data['data']
                    elif isinstance(data['data'], dict) and data['data'].get('results'):
                        listings = data['data']['results']
                
                if listings:
                    # 숙소 이름 매칭
                    for listing in listings[:20]:
                        listing_name = listing.get('name', '') or listing.get('title', '')
                        
                        place_clean = place_name.replace(" ", "").replace("-", "").lower()
                        listing_clean = listing_name.replace(" ", "").replace("-", "").lower()
                        
                        korean_to_english = {'롯데': 'lotte', '호텔': 'hotel', '서울': 'seoul'}
                        place_english = place_clean
                        for kr, en in korean_to_english.items():
                            place_english = place_english.replace(kr, en)
                        
                        if (place_clean in listing_clean or listing_clean in place_clean or
                            place_english in listing_clean or listing_clean in place_english):
                            
                            # 가격 추출
                            price = 0
                            if listing.get('price'):
                                price_data = listing['price']
                                if isinstance(price_data, dict):
                                    price = price_data.get('rate', 0) or price_data.get('total', 0)
                                elif isinstance(price_data, (int, float)):
                                    price = price_data
                            
                            if not price and listing.get('pricing'):
                                pricing = listing['pricing']
                                if isinstance(pricing, dict):
                                    price = (pricing.get('rate', {}).get('amount', 0) or
                                            pricing.get('total', {}).get('amount', 0))
                            
                            # 1박 기준으로 변환
                            if price > 0 and nights > 0:
                                per_night = price / nights
                                logger.info(f"    ✅ Airbnb: {int(per_night):,}원")
                                return {
                                    'platform': 'Airbnb',
                                    'price': int(per_night),
                                    'currency': 'KRW',
                                    'hotel_name': listing_name,
                                    'room_type': '전체 숙소',
                                    'rating': round(listing.get('rating', 0) or listing.get('avgRating', 0), 1)
                                }
        
        logger.warning(f"    ⚠️ Airbnb: '{place_name}' 숙소를 찾을 수 없음")
        return None
    except Exception as e:
        logger.warning(f"    ⚠️ Airbnb error: {e}")
        return None


async def _compare_prices_parallel(place_name: str, check_in: str, check_out: str, num_guests: int, nights: int) -> List[Dict]:
    """3개 플랫폼 병렬 가격 조회 (3배 빠름!)"""
    tasks = [
        _fetch_booking_price_async(place_name, check_in, check_out, num_guests, nights),
        _fetch_agoda_price_async(place_name, check_in, check_out, nights),
        _fetch_airbnb_price_async(place_name, check_in, check_out, num_guests, nights)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # None과 예외 필터링
    prices = []
    for result in results:
        if result and isinstance(result, dict):
            prices.append(result)
    
    return prices


# ============================================================================
# TOOL 1: 숙소 검색 (고급 필터링)
# ============================================================================

@tool
def search_accommodations(
    region: str,
    preference: Optional[str] = None,
    num_results: int = 10,
    min_rating: Optional[float] = None,
    price_level: Optional[int] = None,
    sort_by: str = "rating"
) -> dict:
    """숙소 검색 (고급 필터링 지원)
    
    Args:
        region: 검색 지역 (예: "강릉", "부산 해운대")
        preference: 선호도 (예: "호텔", "펜션")
        num_results: 결과 수 (기본 10개)
        min_rating: 최소 평점 (예: 4.0)
        price_level: 가격대 (0-4)
        sort_by: 정렬 ("rating", "reviews", "price")
    """
    try:
        if not gmaps:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message="Google API 키가 설정되지 않았습니다",
                error="GOOGLE_PLACES_API_KEY not found"
            ).model_dump()
        
        logger.info(f"🔍 숙소 검색: {region} - {preference or '전체'}")
        if min_rating:
            logger.info(f"  📊 필터: 평점 {min_rating}점 이상")
        if price_level is not None:
            price_symbols = ['무료', '$', '$$', '$$$', '$$$$']
            logger.info(f"  💰 필터: {price_symbols[price_level]} 가격대")
        
        # 테마 숙소 키워드 매핑
        THEME_KEYWORDS = {
            "한옥스테이": "한옥 전통 hanok",
            "료칸": "료칸 ryokan 온천",
            "글램핑": "글램핑 glamping 캐핑",
            "풀빌라": "풀빌라 pool villa 수영장",
            "오션뷰": "오션뷰 ocean view 바다",
            "펜션": "펜션 pension 독채",
            "캐핑카": "캐핑카 camping car 이동식",
            "트리하우스": "트리하우스 tree house 나무",
            "컨테이너": "컨테이너 container 감성"
        }
        
        # 모든 숙소 검색에 Serper 웹 검색 우선 사용
        web_place_names = []
        try:
            from agents.tool.serper_helper import search_web_for_theme_accommodations
            logger.info(f"  🌐 Serper 웹 검색 실행...")
            web_place_names = search_web_for_theme_accommodations(region, preference or "숙소", num_results)
            logger.info(f"  ✅ 웹 검색 결과: {len(web_place_names)}개")
        except Exception as e:
            logger.warning(f"  ⚠️ 웹 검색 실패, Google Places로 폴백: {e}")
        
        # 1. 좌표 변환
        geocode_result = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode_result:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message=f"{region} 지역을 찾을 수 없습니다",
                error="Geocoding failed"
            ).model_dump()
        
        coords = geocode_result[0]['geometry']['location']
        
        # 2. 웹 검색 결과로 Google Places 검색
        places = []
        if web_place_names:
            logger.info(f"  🔍 웹 검색 결과로 Google Places 검색...")
            for place_name in web_place_names:
                try:
                    # Text Search로 정확한 장소 찾기
                    text_search_result = gmaps.places(
                        query=f"{place_name} {region}",
                        language="ko"
                    )
                    
                    if text_search_result.get('results'):
                        place = text_search_result['results'][0]
                        if place.get('user_ratings_total', 0) >= 10:  # 최소 리뷰 수
                            places.append(place)
                            logger.info(f"    ✅ {place['name']} - ⭐{place.get('rating', 0)}")
                except Exception as e:
                    logger.warning(f"    ⚠️ {place_name} 검색 실패: {e}")
        
        # 3. 웹 검색 결과가 없으면 기본 Google Places 검색
        if not places:
            logger.info(f"  🔍 Google Places 기본 검색...")
            # 테마 키워드 매핑
            search_keyword = preference
            if preference:
                for theme, keywords in THEME_KEYWORDS.items():
                    if theme in preference:
                        search_keyword = keywords
                        break
            
            results = gmaps.places_nearby(
                location=(coords['lat'], coords['lng']),
                radius=5000,
                type="lodging",
                keyword=search_keyword,
                language="ko"
            )
            
            if not results.get('results') and preference:
                results = gmaps.places_nearby(
                    location=(coords['lat'], coords['lng']),
                    radius=5000,
                    type="lodging",
                    keyword=None,
                    language="ko"
                )
            
            if not results.get('results'):
                return AgentResponse(
                    success=True,
                    agent_name="accommodation",
                    data=[],
                    count=0,
                    message=f"{region}에서 숙소를 찾을 수 없습니다"
                ).model_dump()
            
            places = results['results']
        
        # 4. 필터링 (기본 필터만 - 예약 사이트는 이미 검증됨)
        filtered = [r for r in places if r.get('user_ratings_total', 0) >= 50]
        
        
        if min_rating:
            filtered = [r for r in filtered if r.get('rating', 0) >= min_rating]
        if price_level is not None:
            filtered = [r for r in filtered if r.get('price_level', 0) == price_level]
        
        if not filtered:
            return AgentResponse(
                success=True,
                agent_name="accommodation",
                data=[],
                count=0,
                message=f"{region}에서 조건에 맞는 숙소를 찾을 수 없습니다"
            ).model_dump()

        
        # 4. 정렬
        if sort_by == "rating":
            sorted_results = sorted(filtered, key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)), reverse=True)
        elif sort_by == "reviews":
            sorted_results = sorted(filtered, key=lambda x: x.get('user_ratings_total', 0), reverse=True)
        elif sort_by == "price":
            sorted_results = sorted(filtered, key=lambda x: x.get('price_level', 0))
        else:
            sorted_results = sorted(filtered, key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)), reverse=True)
        
        sorted_results = sorted_results[:num_results]
        
        # 5. 데이터 수집
        places = []
        for place in sorted_results:
            place_id = place['place_id']
            place_price_level = place.get('price_level')
            if place_price_level is None:
                try:
                    details = gmaps.place(place_id, fields=['price_level'], language='ko')
                    place_price_level = details.get('result', {}).get('price_level', 0)
                except:
                    place_price_level = 0
            
            place_data = PlaceData(
                place_id=place_id,
                name=place['name'],
                category="hotel",
                address=place.get('vicinity', ''),
                latitude=place['geometry']['location']['lat'],
                longitude=place['geometry']['location']['lng'],
                region=region,
                rating=place.get('rating', 0),
                review_count=place.get('user_ratings_total', 0),
                price_level=place_price_level,
                google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                tags=[preference] if preference else []
            )
            places.append(place_data)
            logger.info(f"✅ {place_data.name} - ⭐{place_data.rating}")
        
        return AgentResponse(
            success=True,
            agent_name="accommodation",
            data=[p.model_dump() for p in places],
            count=len(places),
            message=f"{region} 숙소 {len(places)}곳 찾음! 🏨"
        ).model_dump()
        
    except Exception as e:
        logger.error(f"❌ 숙소 검색 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="accommodation",
            message="숙소 검색 중 오류 발생",
            error=str(e)
        ).model_dump()


# ============================================================================
# TOOL 2: 리뷰 AI 요약
# ============================================================================

@tool
def summarize_reviews(place_id: str, user_id: Optional[str] = None) -> dict:
    """숙소 리뷰 AI 요약"""
    try:
        if not gmaps or not openai_client:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message="API 키가 설정되지 않았습니다",
                error="Missing API keys"
            ).model_dump()
        
        logger.info(f"📝 리뷰 요약: {place_id}")
        
        # 1. 숙소 정보
        details = gmaps.place(place_id, fields=['name'], language="ko")['result']
        place_name = details.get('name', '알 수 없음')
        
        # 2. 리뷰 수집
        reviews = get_reviews_enhanced(place_id)
        if not reviews:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message=f"{place_name}의 리뷰가 없습니다",
                error="No reviews available"
            ).model_dump()
        
        # 3. 평점 분포
        rating_dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for review in reviews:
            rating = review.get('rating', 0)
            if rating in rating_dist:
                rating_dist[rating] += 1
        
        # 4. 트렌드 분석
        sorted_reviews = sorted(reviews, key=lambda x: x.get('time', 0), reverse=True)
        recent_count = min(len(sorted_reviews) // 2, 3)
        recent_reviews_data = sorted_reviews[:recent_count]
        older_reviews_data = sorted_reviews[recent_count:recent_count*2]
        
        recent_avg = sum(r.get('rating', 0) for r in recent_reviews_data) / len(recent_reviews_data) if recent_reviews_data else 0
        older_avg = sum(r.get('rating', 0) for r in older_reviews_data) / len(older_reviews_data) if older_reviews_data else 0
        trend_direction = "상승" if recent_avg > older_avg else "하락" if recent_avg < older_avg else "유지"
        
        # 5. OpenAI 요약
        review_texts = []
        for review in sorted_reviews:
            text = review.get('text', '')
            if text:
                review_texts.append(f"[{review.get('rating', 0)}점] {text}")
        
        reviews_combined = "\n\n".join(review_texts)
        prompt = f"""'{place_name}' 숙소 리뷰를 분석하여 요약해주세요.

리뷰:
{reviews_combined}

형식:
1. 전체 요약 (2-3문장)
2. 주요 장점 3개
3. 주요 단점 3개
4. 최근 변화"""
        
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "여행 숙소 리뷰 분석 전문가"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            ai_summary = completion.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ OpenAI 요약 실패: {e}")
            ai_summary = "AI 요약 생성 실패"
        
        result_data = {
            'place_id': place_id,
            'place_name': place_name,
            'ai_summary': ai_summary,
            'rating_distribution': rating_dist,
            'total_reviews': len(reviews),
            'trend_analysis': {
                'recent_avg_rating': round(recent_avg, 1),
                'older_avg_rating': round(older_avg, 1),
                'trend_direction': trend_direction,
                'rating_change': round(recent_avg - older_avg, 1)
            }
        }
        
        return AgentResponse(
            success=True,
            agent_name="accommodation",
            data=[result_data],
            count=1,
            message=f"{place_name} 리뷰 요약 완료! 📝"
        ).model_dump()
        
    except Exception as e:
        logger.error(f"❌ 리뷰 요약 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="accommodation",
            message="리뷰 요약 중 오류 발생",
            error=str(e)
        ).model_dump()


# ============================================================================
# TOOL 3: 가격 비교 (병렬 처리!)
# ============================================================================

@tool
def compare_booking_prices(
    place_name: str,
    check_in: str,
    check_out: str,
    num_guests: int = 2,
    location: str = "서울"
) -> dict:
    """예약 사이트 실시간 최저가 비교 - 병렬 처리로 3배 빠름!"""
    try:
        if not RAPIDAPI_KEY:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message="RapidAPI 키가 설정되지 않았습니다",
                error="RAPIDAPI_KEY not found"
            ).model_dump()
        
        logger.info(f"💰 가격 비교: {place_name} ({check_in} ~ {check_out})")
        
        # 날짜 계산
        checkin_date = datetime.strptime(check_in, "%Y-%m-%d")
        checkout_date = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (checkout_date - checkin_date).days
        
        # 캐시 확인
        cache_key = f"{place_name}_{check_in}_{check_out}_{num_guests}"
        if cache_key in _price_cache:
            cached_data, timestamp = _price_cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
                logger.info("✅ 캐시에서 반환 (즉시 응답)")
                return cached_data
        
        # 병렬 조회! (3배 빠름!)
        prices = asyncio.run(_compare_prices_parallel(place_name, check_in, check_out, num_guests, nights))
        
        if not prices:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message=f"{place_name}의 가격 정보를 찾을 수 없습니다",
                error="No prices found"
            ).model_dump()
        
        # 최저가 찾기
        lowest = min(prices, key=lambda x: x['price'])
        prices_sorted = sorted(prices, key=lambda x: x['price'])
        
        logger.info(f"✅ 가격 비교 완료: {len(prices)}개 플랫폼, 최저가 {lowest['platform']} {lowest['price']:,}원")
        
        response = AgentResponse(
            success=True,
            agent_name="accommodation",
            data=[{
                'place_name': place_name,
                'check_in': check_in,
                'check_out': check_out,
                'nights': nights,
                'num_guests': num_guests,
                'prices': prices_sorted,
                'lowest_price': lowest,
                'total_platforms': len(prices),
                'per_night': True
            }],
            count=len(prices),
            message=f"{place_name} 최저가: {lowest['platform']} {lowest['price']:,}원/박"
        )
        
        # 캐싱
        _price_cache[cache_key] = (response.model_dump(), datetime.now())
        
        return response.model_dump()
        
    except Exception as e:
        logger.error(f"❌ 가격 비교 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="accommodation",
            message="가격 비교 중 오류 발생",
            error=str(e)
        ).model_dump()


# ============================================================================
# TOOL 4: AI 맞춤 추천
# ============================================================================

@tool
def get_recommended_accommodations(
    region: str,
    user_preference: str,
    num_results: int = 3
) -> dict:
    """AI 기반 숙소 추천"""
    try:
        if not openai_client:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message="OpenAI API 키가 설정되지 않았습니다",
                error="OPENAI_API_KEY not found"
            ).model_dump()
        
        logger.info(f"🤖 AI 추천: {region} - '{user_preference}'")
        
        # 1. 쿼리 해석
        import json
        
        interpretation_prompt = f"""사용자가 "{user_preference}"라고 검색했습니다.
다음 정보를 추출해주세요:

1. theme: 테마 (한옥, 료칸, 모던 등)
2. atmosphere: 분위기 (조용한, 아늑한 등)
3. facilities: 시설 (수영장, 온천 등)
4. search_keywords: Google Places 검색 키워드 3-5개

JSON 형식으로 응답:
{{"theme": [], "atmosphere": [], "facilities": [], "search_keywords": []}}"""
        
        interpretation_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "숙소 검색 쿼리 분석 전문가"},
                {"role": "user", "content": interpretation_prompt}
            ],
            temperature=0.3
        )
        
        query_interpretation = json.loads(interpretation_response.choices[0].message.content)
        search_keywords = query_interpretation.get('search_keywords', [])
        search_preference = " ".join(search_keywords[:3]) if search_keywords else None
        
        # 2. 숙소 검색
        search_result = search_accommodations.func(region, preference=search_preference, num_results=15)
        
        if not search_result['success'] or not search_result['data']:
            return AgentResponse(
                success=False,
                agent_name="accommodation",
                message=f"{region}에서 숙소를 찾을 수 없습니다",
                error="No accommodations found"
            ).model_dump()
        
        places = search_result['data']
        
        # 3. AI 추천
        places_summary = [{'name': p['name'], 'rating': p['rating'], 'review_count': p['review_count']} for p in places]
        
        recommendation_prompt = f"""사용자가 "{user_preference}"를 검색했습니다.
다음 숙소 중 {num_results}곳을 추천해주세요:
{json.dumps(places_summary, ensure_ascii=False)}

JSON 형식:
{{"recommendations": [{{"name": "호텔명", "score": 95, "reason": "이유", "pros": ["장점1", "장점2", "장점3"], "cons": ["주의사항1"]}}]}}"""
        
        recommendation_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "한국 여행 숙소 추천 전문가"},
                {"role": "user", "content": recommendation_prompt}
            ],
            temperature=0.7
        )
        
        ai_result = json.loads(recommendation_response.choices[0].message.content)
        recommendations = ai_result.get('recommendations', [])
        
        # 4. place_id 결합
        final_recommendations = []
        for rec in recommendations[:num_results]:
            matching_place = next((p for p in places if p['name'] == rec['name']), None)
            if matching_place:
                final_recommendations.append({
                    **rec,
                    'place_id': matching_place['place_id'],
                    'rating': matching_place['rating'],
                    'google_maps_url': matching_place['google_maps_url']
                })
        
        return AgentResponse(
            success=True,
            agent_name="accommodation",
            data=[{
                'region': region,
                'user_preference': user_preference,
                'query_interpretation': query_interpretation,
                'recommendations': final_recommendations
            }],
            count=len(final_recommendations),
            message=f"'{user_preference}' 맞춤 추천 {len(final_recommendations)}곳!"
        ).model_dump()
        
    except Exception as e:
        logger.error(f"❌ AI 추천 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="accommodation",
            message="AI 추천 중 오류 발생",
            error=str(e)
        ).model_dump()


# ============================================================================
# TOOL LIST (에이전트에서 import용)
# ============================================================================

accommodation_tools = [
    search_accommodations,
    summarize_reviews,
    compare_booking_prices,
    get_recommended_accommodations
]
