"""맛집 추천 관련 LangChain 툴 모음 (최종 - 5개)"""
from langchain.tools import tool
from typing import Optional, List


@tool
def search_restaurants_tool(
    region: str,
    preference: Optional[str] = None,
    age_group: Optional[str] = None,
    gender: Optional[str] = None,
    companion: Optional[str] = None,
    occasion: Optional[str] = None,
    dietary_restrictions: Optional[List[str]] = None,
    sort_by: str = "review_count",
    num_results: int = 5  # 상위 5개
) -> str:
    """
    특정 지역의 맛집 검색 (고도화)
    
    Args:
        region: 검색 지역
        preference: 음식 선호
        age_group: 연령대
        gender: 성별
        companion: 동행자
        occasion: 상황
        dietary_restrictions: 식단 제한
        sort_by: 정렬 기준
        num_results: 결과 개수 (기본 5개)
    
    Returns:
        str: 포맷된 맛집 리스트 (시그니처 메뉴 설명 포함)
    """
    from agents.restaurant_agent import search_restaurants
    from langchain_openai import ChatOpenAI
    import os
    
    # 최대 5개 제한
    num_results = min(num_results, 5)
    
    result = search_restaurants(region, preference, age_group, gender, companion, occasion, dietary_restrictions, sort_by, num_results)
    
    if not result.success or result.count == 0:
        return f"❌ {result.message}"
    
    # 친근한 인사말
    greeting = ""
    if companion == "데이트":
        greeting = "데이트하기 좋은 "
    elif companion == "가족":
        greeting = "가족과 함께하기 좋은 "
    elif companion == "회식":
        greeting = "회식하기 좋은 "
    
    output = [f"🍽️ {greeting}**{region} 맛집** 추천드려요!\n"]
    
    # LLM으로 모든 맛집 설명 한 번에 생성 (최적화!)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))
    
    # 모든 맛집 정보를 한 번에 전달
    restaurants_info = "\n".join([
        f"{i+1}. {place['name']} (평점: {place['rating']}점)"
        for i, place in enumerate(result.data)
    ])
    
    prompt = f"""다음 맛집들의 특징을 각각 한 줄로 설명해주세요:

{restaurants_info}

각 가게가 **무엇으로 유명한지, 시그니처 메뉴가 뭐지** 추측해서 설명하세요.
예시:
- "낙지소면과 불고기가 유명한 한식당이에요"
- "파스타와 리조또가 맛있는 이탈리안 레스토랑이에요"
- "삼겹살 맛집으로 유명해요"

각 맛집마다 한 줄씩, 번호 없이 설명만 출력하세요.
{len(result.data)}개의 설명을 줄바꿈으로 구분하여 출력하세요."""
    
    try:
        descriptions_text = llm.invoke(prompt).content.strip()
        descriptions = descriptions_text.split('\n')
        # 빈 줄 제거
        descriptions = [d.strip().strip('"').strip("'") for d in descriptions if d.strip()]
    except:
        descriptions = [f"평점 {place['rating']}점의 인기 맛집이에요!" for place in result.data]
    
    # 설명 개수가 맞지 않으면 기본 설명 사용
    if len(descriptions) != len(result.data):
        descriptions = [f"평점 {place['rating']}점의 인기 맛집이에요!" for place in result.data]
    
    for i, place in enumerate(result.data, 1):
        output.append(f"**{i}. {place['name']}**")
        output.append(f"💬 {descriptions[i-1]}")
        output.append(f"⭐ **{place['rating']}점** · 리뷰 {place['review_count']:,}개")
        
        # 영업 상태
        status_line = []
        if place.get('open_now') is not None:
            status = "🟢 영업중" if place['open_now'] else "🔴 영업종료"
            status_line.append(status)
        
        if place.get('opening_hours'):
            import datetime
            today_idx = datetime.datetime.now().weekday()
            hours = place['opening_hours']
            if hours and len(hours) > today_idx:
                time_only = hours[today_idx].split(': ', 1)[-1]
                status_line.append(time_only)
        
        if status_line:
            output.append(" · ".join(status_line))
        
        output.append(f"📍 {place['address']}")
        
        if place.get('phone'):
            output.append(f"📞 {place['phone']}")
        
        output.append(f"[🗺️ 지도보기]({place['google_maps_url']})\n")
    
    output.append("맛있게 드세요! 😊")
    
    return "\n".join(output)


@tool
def get_restaurant_reviews_tool(place_id: str, num_reviews: int = 20) -> str:
    """
    특정 맛집의 리뷰 요약
    
    Args:
        place_id: Google Place ID
        num_reviews: 분석할 리뷰 개수
    
    Returns:
        str: 포맷된 리뷰 요약
    """
    from agents.restaurant_agent import get_restaurant_reviews
    result = get_restaurant_reviews(place_id, num_reviews)
    
    if not result.success or result.count == 0:
        return f"❌ {result.message}"
    
    data = result.data[0]
    output = [f"📝 **{data['place_name']}** 리뷰\n"]
    
    # 요약 (간결하게)
    summary = data['summary']
    if len(summary) > 100:
        summary = summary[:100] + "..."
    output.append(f"💬 {summary}\n")
    
    # 장점 (최대 3개)
    if data.get('pros'):
        output.append("**👍 장점**")
        for pro in data['pros'][:3]:
            output.append(f"• {pro}")
        output.append("")
    
    # 단점 (최대 2개)
    if data.get('cons'):
        output.append("**👎 단점**")
        for con in data['cons'][:2]:
            output.append(f"• {con}")
        output.append("")
    
    # 추천 메뉴
    if data.get('recommended_menu'):
        menus = ', '.join(data['recommended_menu'][:3])
        output.append(f"**🍽️ 추천** {menus}")
    
    return "\n".join(output)


@tool
def extract_menu_tool(place_id: str, num_reviews: int = 20) -> str:
    """
    리뷰에서 메뉴 추출
    
    Args:
        place_id: Google Place ID
        num_reviews: 분석할 리뷰 개수
    
    Returns:
        str: 포맷된 메뉴 정보
    """
    from agents.restaurant_agent import extract_menu
    result = extract_menu(place_id, num_reviews)
    
    if not result.success or result.count == 0:
        return f"❌ {result.message}"
    
    data = result.data[0]
    output = [f"🍽️ **{data['place_name']}** 메뉴\n"]
    
    # 시그니처 메뉴
    if data.get('signature_menu'):
        sig_menus = ', '.join(data['signature_menu'][:3])
        output.append(f"**⭐ 시그니처** {sig_menus}")
    
    # 인기 메뉴
    if data.get('popular_menu'):
        pop_menus = ', '.join(data['popular_menu'][:3])
        output.append(f"**🔥 인기** {pop_menus}")
    
    # 가격 정보
    if data.get('price_info') and not data['price_info'].startswith('가격대 정보'):
        output.append(f"\n**💰 가격** {data['price_info']}")
    
    return "\n".join(output)


@tool
def verify_restaurant_tool(place_id: str, user_location: Optional[tuple] = None) -> str:
    """
    맛집 검증 및 신뢰도 점수
    
    Args:
        place_id: Google Place ID
        user_location: 사용자 위치 (lat, lng)
    
    Returns:
        str: 포맷된 검증 결과
    """
    from agents.restaurant_agent import verify_restaurant
    result = verify_restaurant(place_id, user_location)
    
    if not result.success or result.count == 0:
        return f"❌ {result.message}"
    
    data = result.data[0]
    output = [f"🔍 **{data['place_name']}** 검증\n"]
    
    # 신뢰도 점수
    score = data['total_score']
    grade = data['grade']
    
    # 등급별 이모지
    grade_emoji = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "❌"}
    emoji = grade_emoji.get(grade, "")
    
    output.append(f"{emoji} **{score}점** ({grade}등급) - {data['trust_level']}")
    
    # 주요 통계
    stats = data['stats']
    output.append(f"⭐ {stats['rating']}점 · 리뷰 {stats['review_count']:,}개 · 최근 {stats['recent_reviews']}개\n")
    
    # 경고
    if data.get('warnings'):
        for warning in data['warnings']:
            output.append(f"⚠️ {warning}")
    
    return "\n".join(output)


@tool
def get_restaurant_details_tool(place_id: str) -> str:
    """
    맛집 상세 정보 (예약/가격/주차/애완견)
    
    Args:
        place_id: Google Place ID
    
    Returns:
        str: 포맷된 상세 정보
    """
    from agents.restaurant_agent import get_all_restaurant_info
    details = get_all_restaurant_info(place_id)
    
    output = ["📋 **상세 정보**\n"]
    
    # 예약
    reservation = details.get('reservation', {})
    if reservation.get('reservation_required'):
        output.append("📅 **예약** 필수 (전화/온라인)")
    else:
        output.append("📅 **예약** 권장")
    
    # 가격
    price = details.get('price', {})
    if price.get('recommended_budget'):
        output.append(f"💰 **가격** {price['recommended_budget']} ({price.get('budget_level', '보통')})")
    
    # 주차
    parking = details.get('parking', {})
    if parking.get('available') is True:
        output.append(f"🅿️ **주차** 가능 ({parking.get('type', '')})")
    elif parking.get('available') is False:
        output.append("🅿️ **주차** 어려움")
    else:
        output.append("🅿️ **주차** 정보 없음")
    
    # 애완견
    pet = details.get('pet', {})
    if pet.get('pet_allowed') is True:
        output.append("🐕 **반려견** 동반 가능")
    elif pet.get('pet_allowed') is False:
        output.append("🐕 **반려견** 동반 불가")
    else:
        output.append("🐕 **반려견** 정보 없음")
    
    return "\n".join(output)
