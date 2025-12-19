# tools/shopping_search_tool.py

import os
from typing import List, Dict, Any

from dotenv import load_dotenv
import googlemaps
from langchain_core.tools import tool

load_dotenv()

# Google Maps API 키
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# 대형마트 제외 키워드 (편의점 필터링용)
LARGE_MART_KEYWORDS = [
    "이마트", "홈플러스", "롯데마트", "메가마트", "빅마켓",
    "하나로마트", "농협", "코스트코", "emart", "homeplus",
]

# 실제 편의점 체인
CONVENIENCE_STORE_CHAINS = [
    "GS25", "CU", "세븐일레븐", "7-ELEVEN", "이마트24", "씨유", "미니스톱",
]


# --------------------
# 카테고리 판별 함수들
# --------------------

def is_convenience_store_search(user_input: str) -> bool:
    """편의점 검색인지 확인"""
    convenience_keywords = ["편의점", "cvs", "씨유", "GS25", "세븐일레븐", "cu"]
    return any(keyword in user_input for keyword in convenience_keywords)


def is_pharmacy_search(user_input: str) -> bool:
    """약국 검색인지 확인"""
    pharmacy_keywords = ["약국", "pharmacy", "약방", "드럭스토어"]
    return any(keyword in user_input for keyword in pharmacy_keywords)


def is_large_mart_search(user_input: str) -> bool:
    """대형마트 검색인지 확인"""
    large_mart_keywords = ["대형마트", "마트", "슈퍼마켓", "supermarket"]
    return any(keyword in user_input for keyword in large_mart_keywords)


def get_category_from_input(user_input: str) -> str:
    """
    사용자 입력에서 카테고리 추출
    """
    categories = {
        "편의점": ["편의점", "cvs", "씨유", "GS25", "세븐일레븐", "cu"],
        "대형마트": ["대형마트", "마트", "이마트", "홈플러스", "롯데마트"],
        "팝업스토어": ["팝업", "팝업스토어", "popup"],
        "다이소": ["다이소", "daiso"],
        "약국": ["약국", "pharmacy"],
        "재래시장": ["재래시장", "시장", "전통시장"],
    }

    text = user_input.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category
    return ""

def get_implied_category_from_product(user_input: str) -> str | None:
    """
    상품/목적 키워드로부터 적절한 쇼핑 카테고리를 유추한다.

    예:
    - '고기 사러 갈 곳' -> '대형마트'
    - '와인오프너 파는 곳' -> '다이소'
    - '콘돔 파는 곳' -> '편의점'
    """
    text = user_input.lower()

    # 1) 대형마트로 보내야 하는 키워드들 (고기, 장보기 계열)
    large_mart_keywords = [
        "고기", "삼겹살", "목살", "소고기", "돼지고기",
        "장보기", "장 보러", "장 보러 갈", "정육", "정육점",
    ]
    for kw in large_mart_keywords:
        if kw in text:
            return "대형마트"

    # 2) 다이소/생활용품점 계열
    daiso_keywords = [
        "와인오프너", "와인 오프너", "병따개", "병 따개",
        "와인 따개", "오프너", "주방용품", "생활용품",
    ]
    for kw in daiso_keywords:
        if kw in text:
            return "다이소"

    # 3) 약국 계열 (감기약, 두통약 등)
    pharmacy_keywords = [
        "감기약", "두통약", "해열제", "종합감기약", "기침약",
        "감기 약", "두통 약", "약 필요", "약 사러", "약 파는",
    ]
    for kw in pharmacy_keywords:
        if kw in text:
            return "약국"

    # 4) 편의점/약국 계열 (일단 편의점 우선)
    convenience_keywords = [
        "콘돔", "피임도구", "피임 도구", "피임기구", "피임 기구",
        "야간 간식", "야식 사러", "컵라면 사러",
    ]
    for kw in convenience_keywords:
        if kw in text:
            return "편의점"

    return None

def has_category_keyword(user_input: str) -> bool:
    """
    쇼핑 관련 카테고리 키워드 또는
    상품 키워드(고기/와인오프너/콘돔 등)가 있는지 여부 판별.

    - 매장 타입 키워드(편의점/마트/다이소/약국/시장) 있으면 True
    - 매장 타입은 없지만 상품 키워드로 카테고리를 유추할 수 있어도 True
    """
    if get_category_from_input(user_input) != "":
        return True
    if get_implied_category_from_product(user_input) is not None:
        return True
    return False

def get_category_hint(user_input: str) -> str:
    """
    추천/프롬프트에서 사용할 카테고리 힌트를 일관되게 계산한다.

    우선순위:
    1) 명시적 카테고리 키워드 (편의점/약국/대형마트 등)
    2) 상품 키워드 기반 유추 카테고리
    3) 기본값: '쇼핑 장소'
    """
    # 1. 명시적 카테고리
    explicit = get_category_from_input(user_input)
    implied = get_implied_category_from_product(user_input)

    # 대표 카테고리 문자열 결정
    # -> 이 함수에서는 최종 문자열만 필요
    if is_pharmacy_search(user_input) or explicit == "약국" or implied == "약국":
        return "약국"
    if is_convenience_store_search(user_input) or explicit == "편의점" or implied == "편의점":
        return "편의점"
    if is_large_mart_search(user_input) or explicit == "대형마트" or implied == "대형마트":
        return "대형마트"

    # 다이소 등 기타 카테고리
    if explicit:
        return explicit
    if implied:
        return implied

    return "쇼핑 장소"


# --------------------
# 결과 필터링 함수들
# --------------------

def filter_convenience_stores(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """실제 편의점만 필터링 (대형마트 제외)"""
    filtered = []
    for place in places:
        name = place["name"]
        # 대형마트 키워드 제외
        if not any(keyword in name for keyword in LARGE_MART_KEYWORDS):
            filtered.append(place)
    return filtered


def filter_large_marts(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """대형마트 검색 시 편의점 제외"""
    filtered = []
    for place in places:
        name = place["name"]
        # 편의점 체인 제외
        if not any(keyword in name for keyword in CONVENIENCE_STORE_CHAINS):
            filtered.append(place)
    return filtered


def filter_by_brand(places: List[Dict[str, Any]], brand_keyword: str) -> List[Dict[str, Any]]:
    """특정 브랜드/키워드가 포함된 장소만 필터링"""
    filtered = []
    for place in places:
        if brand_keyword in place["name"]:
            filtered.append(place)
    return filtered


# --------------------
# 실제 Google Places 검색 함수 (로우레벨)
# --------------------

def search_shopping_places(
    region: str,
    num_results: int = 5,
    is_convenience: bool = False,
    is_pharmacy: bool = False,
    is_large_mart: bool = False,
    keyword: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Google Places API를 사용하여 실제 쇼핑 장소 검색

    Args:
        region: 검색 지역 (예: '하남', '잠실')
        num_results: 반환할 결과 개수
        is_convenience: 편의점 검색 여부
        is_pharmacy: 약국 검색 여부
        is_large_mart: 대형마트 검색 여부
        keyword: 검색 키워드 (예: "다이소", "이마트" 등)
    """
    if not gmaps:
        print("❌ Google Places API 키가 설정되지 않았습니다.")
        return []

    try:
        # 1. 좌표 변환
        geocode_result = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode_result:
            print(f"❌ 지역을 찾을 수 없습니다: {region}")
            return []

        coords = geocode_result[0]["geometry"]["location"]

        # 2. place type 결정
        if is_pharmacy:
            search_types = ["pharmacy"]
        elif is_large_mart:
            search_types = ["supermarket", "department_store"]
        elif is_convenience:
            search_types = ["convenience_store"]
        else:
            # 범용 쇼핑 검색
            search_types = [
                "shopping_mall",
                "supermarket",
                "convenience_store",
                "department_store",
            ]

        all_places: List[Dict[str, Any]] = []

        # 3. 타입별로 검색
        for place_type in search_types:
            params: Dict[str, Any] = {
                "location": (coords["lat"], coords["lng"]),
                "radius": 3000,  # 3km
                "type": place_type,
                "language": "ko",
            }
            if keyword:
                params["keyword"] = keyword

            results = gmaps.places_nearby(**params)

            for place in results.get("results", []):
                # 좌표 먼저 꺼내고
                loc = place["geometry"]["location"]
                lat = loc["lat"]
                lng = loc["lng"]

                # ▶ 구글맵에서 바로 볼 수 있는 URL 생성
                map_url = (
                    "https://www.google.com/maps/search/"
                    f"?api=1&query={lat},{lng}&query_place_id={place['place_id']}"
                )

                place_info = {
                    "place_id": place["place_id"],
                    "name": place["name"],
                    "rating": place.get("rating", 0),
                    "review_count": place.get("user_ratings_total", 0),
                    "address": place.get("vicinity", ""),
                    "types": place.get("types", []),
                    "lat": lat,
                    "lng": lng,
                    "map_url": map_url,  # 👈 여기 추가
                }
                all_places.append(place_info)


        # 4. 카테고리별 후처리 필터
        if is_convenience:
            all_places = filter_convenience_stores(all_places)
        if is_large_mart:
            all_places = filter_large_marts(all_places)
        if keyword:
            all_places = filter_by_brand(all_places, keyword)

        # 5. 평점 기준 정렬 + 중복 제거(이름 기준)
        sorted_places = sorted(all_places, key=lambda x: x["rating"], reverse=True)

        seen_names: set[str] = set()
        unique_places: List[Dict[str, Any]] = []
        for place in sorted_places:
            if place["name"] not in seen_names:
                unique_places.append(place)
                seen_names.add(place["name"])

        return unique_places[:num_results]

    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return []

def search_shopping_places_by_coords(
    lat: float,
    lng: float,
    num_results: int = 5,
    is_convenience: bool = False,
    is_pharmacy: bool = False,
    is_large_mart: bool = False,
    keyword: str | None = None,
) -> List[Dict[str, Any]]:
    """
    (현재 위치용) 위도/경도 기반 쇼핑 장소 검색

    Args:
        lat, lng: 현재 위치 좌표
        num_results: 반환할 결과 개수
        is_convenience: 편의점 검색 여부
        is_pharmacy: 약국 검색 여부
        is_large_mart: 대형마트 검색 여부
        keyword: 검색 키워드 (예: "다이소", "이마트" 등)
    """
    if not gmaps:
        print("❌ Google Places API 키가 설정되지 않았습니다.")
        return []

    try:
        coords = {"lat": lat, "lng": lng}

        # 1. place type 결정
        if is_pharmacy:
            search_types = ["pharmacy"]
        elif is_large_mart:
            search_types = ["supermarket", "department_store"]
        elif is_convenience:
            search_types = ["convenience_store"]
        else:
            # 범용 쇼핑 검색
            search_types = [
                "shopping_mall",
                "supermarket",
                "convenience_store",
                "department_store",
            ]

        all_places: List[Dict[str, Any]] = []

        # 2. 타입별로 검색
        for place_type in search_types:
            params: Dict[str, Any] = {
                "location": (coords["lat"], coords["lng"]),
                "radius": 3000,  # 3km
                "type": place_type,
                "language": "ko",
            }
            if keyword:
                params["keyword"] = keyword

            results = gmaps.places_nearby(**params)

            for place in results.get("results", []):
                loc = place["geometry"]["location"]
                plat = loc["lat"]
                plng = loc["lng"]

                map_url = (
                    "https://www.google.com/maps/search/"
                    f"?api=1&query={plat},{plng}&query_place_id={place['place_id']}"
                )

                place_info = {
                    "place_id": place["place_id"],
                    "name": place["name"],
                    "rating": place.get("rating", 0),
                    "review_count": place.get("user_ratings_total", 0),
                    "address": place.get("vicinity", ""),
                    "types": place.get("types", []),
                    "lat": plat,
                    "lng": plng,
                    "map_url": map_url,
                }
                all_places.append(place_info)

        # 3. 카테고리별 후처리 필터
        if is_convenience:
            all_places = filter_convenience_stores(all_places)
        if is_large_mart:
            all_places = filter_large_marts(all_places)
        if keyword:
            all_places = filter_by_brand(all_places, keyword)

        # 4. 평점 기준 정렬 + 중복 제거(이름 기준)
        sorted_places = sorted(all_places, key=lambda x: x["rating"], reverse=True)

        seen_names: set[str] = set()
        unique_places: List[Dict[str, Any]] = []
        for place in sorted_places:
            if place["name"] not in seen_names:
                unique_places.append(place)
                seen_names.add(place["name"])

        return unique_places[:num_results]

    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return []

# --------------------
# high-level 검색 함수 (agent가 쓰는 진입점)
# --------------------

@tool
def search_shopping_tool(region: str, user_input: str) -> List[Dict[str, Any]]:
    """
    [서치용 툴 - 고수준 함수]

    - 사용자 입력에서 카테고리/브랜드 추출
    - 편의점/약국/대형마트 여부 판단
    - search_shopping_places(...) 호출해서 결과 리스트 반환
    """
    print(f"[Shopping Search] 검색 시작: region={region}, user_input={user_input}")

    # 1. 카테고리/키워드 분석
    is_convenience = is_convenience_store_search(user_input)
    is_pharmacy = is_pharmacy_search(user_input)
    is_large_mart = is_large_mart_search(user_input)

    # 1-1. 명시적 카테고리 (편의점/마트/다이소/약국/시장)
    category = get_category_from_input(user_input)

    # 1-2. 명시적 카테고리가 없으면, 상품 키워드로 유추
    implied_category = get_implied_category_from_product(user_input)
    if not category and implied_category:
        category = implied_category
        print(f"  → 상품 키워드로 유추된 카테고리: {category}")

    # 1-3. 유추된 카테고리에 따라 타입 플래그 보정
    if category == "편의점" and not is_convenience:
        is_convenience = True
    if category == "대형마트" and not is_large_mart:
        is_large_mart = True
    # 약국으로 유추되면 is_pharmacy True로(필요하면 확장)
    if category == "약국" and not is_pharmacy:
        is_pharmacy = True

    keyword = None

    # 브랜드 검색용 (다이소, 이마트, 홈플 등)
    brand_like_categories = ["다이소", "이마트", "홈플러스", "롯데마트", "코스트코"]
    if category in brand_like_categories:
        keyword = category


    if is_convenience:
        print("  → 편의점 검색 모드")
    if is_pharmacy:
        print("  → 약국 검색 모드")
    if is_large_mart:
        print("  → 대형마트 검색 모드")
    if keyword:
        print(f"  → 브랜드 키워드 검색: {keyword}")

    # 2. 실제 검색 수행
    results = search_shopping_places(
        region=region,
        num_results=15,
        is_convenience=is_convenience,
        is_pharmacy=is_pharmacy,
        is_large_mart=is_large_mart,
        keyword=keyword,
    )

    print(f"[Shopping Search] 검색 결과: {len(results)}개")
    return results

def search_shopping_by_coords(
    lat: float,
    lng: float,
    user_input: str,
) -> List[Dict[str, Any]]:
    """
    [현재 위치용 고수준 검색 함수]

    - 사용자 입력에서 카테고리/브랜드/상품 키워드 분석
    - 편의점/약국/대형마트 여부 판단
    - search_shopping_places_by_coords(...) 호출해서 결과 리스트 반환
    """
    print(f"[Shopping Search - Nearby] 검색 시작: lat={lat}, lng={lng}, user_input={user_input}")

    # 1. 카테고리/키워드 분석 (텍스트 기반 로직은 기존과 동일)
    is_convenience = is_convenience_store_search(user_input)
    is_pharmacy = is_pharmacy_search(user_input)
    is_large_mart = is_large_mart_search(user_input)

    category = get_category_from_input(user_input)
    implied_category = get_implied_category_from_product(user_input)
    if not category and implied_category:
        category = implied_category
        print(f"  → 상품 키워드로 유추된 카테고리: {category}")

    if category == "편의점" and not is_convenience:
        is_convenience = True
    if category == "대형마트" and not is_large_mart:
        is_large_mart = True
    if category == "약국" and not is_pharmacy:
        is_pharmacy = True

    keyword = None
    brand_like_categories = ["다이소", "이마트", "홈플러스", "롯데마트", "코스트코"]
    if category in brand_like_categories:
        keyword = category

    if is_convenience:
        print("  → (현재 위치) 편의점 검색 모드")
    if is_pharmacy:
        print("  → (현재 위치) 약국 검색 모드")
    if is_large_mart:
        print("  → (현재 위치) 대형마트 검색 모드")
    if keyword:
        print(f"  → (현재 위치) 브랜드 키워드 검색: {keyword}")

    # 2. 실제 검색 수행 (위도/경도 기반)
    results = search_shopping_places_by_coords(
        lat=lat,
        lng=lng,
        num_results=15,
        is_convenience=is_convenience,
        is_pharmacy=is_pharmacy,
        is_large_mart=is_large_mart,
        keyword=keyword,
    )

    print(f"[Shopping Search - Nearby] 검색 결과: {len(results)}개")
    return results