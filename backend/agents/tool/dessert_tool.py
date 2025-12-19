"""디저트 멀티 툴 - 4가지 핵심 기능 (비교 기능 제거됨)"""
from langchain.tools import tool
from typing import Optional
import sys
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ========================================
# 툴 1: TOP 5 카페 통합 리포트
# ========================================
@tool
def recommend_top_5_desserts_tool(region: str, keyword: str, persona_data: Optional[dict] = None) -> str:
    """
    주변 카페/디저트 맛집 15곳을 검색하고, 평점과 리뷰를 분석해 
    가장 좋은 'TOP 5' 곳의 상세 리포트를 보여줍니다.
    """
    logger.info(f"TOP 5 카페 검색 시작: {region}")
    from agents.dessert_agent import get_top_5_desserts_ux
    from schemas.data_models import UserPersona
    persona = UserPersona(**persona_data) if persona_data else None
    result = get_top_5_desserts_ux(region, keyword, persona)
    if result.success: return result.data[0]['full_report']
    else: return f"오류: {result.error}"

# ========================================
# 툴 2: 카페 리스트 간단 검색
# ========================================
@tool
def search_cafe_list_tool(region: str, keyword: str = "카페", num_results: int = 5) -> dict:
    """
    상세 분석 없이 카페 리스트만 빠르게 검색합니다.
    """
    logger.info(f"카페 리스트 검색: {region} - {keyword}")
    from agents.dessert_agent import search_desserts_integrated
    result = search_desserts_integrated(region, keyword, num_results=min(num_results, 10))
    if result.success:
        cafe_list = []
        for i, place in enumerate(result.data, 1):
            cafe_list.append({
                "순위": i, "이름": place['name'], "평점": f"⭐{place['rating']}",
                "리뷰수": f"{place['review_count']}개", "주소": place['address'],
                "지도": place['google_maps_url']
            })
        return {"success": True, "region": region, "total": len(cafe_list), "cafes": cafe_list}
    else: return {"success": False, "error": result.error}

# ========================================
# 툴 3: 특정 카페 상세 분석
# ========================================
@tool
def analyze_cafe_detail_tool(place_id: str, persona_data: Optional[dict] = None) -> str:
    """
    특정 카페의 place_id를 입력하면 해당 카페만 상세 분석합니다.
    """
    logger.info(f"카페 상세 분석: {place_id}")
    from agents.dessert_agent import generate_korean_ux_report
    from schemas.data_models import UserPersona
    persona = UserPersona(**persona_data) if persona_data else None
    result = generate_korean_ux_report(place_id, persona)
    if result.success: return result.data[0]['formatted_report']
    else: return f"실패: {result.error}"

# ========================================
# 툴 4: 지역별 카페 가격 분석
# ========================================
@tool
def analyze_cafe_price_tool(region: str, menu_type: str = "커피") -> str:
    """
    특정 지역의 카페 메뉴 가격대를 분석합니다 (구체적인 가격 정보 포함).
    """
    logger.info(f"가격 분석: {region} - {menu_type}")
    from agents.dessert_agent import get_cafe_price_analysis
    result = get_cafe_price_analysis(region, menu_type)
    if result.success: return result.data[0]['price_report']
    else: return f"실패: {result.error}"

# ========================================
# 테스트 실행부 (로그 포맷 개선)
# ========================================
def print_header(title):
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

if __name__ == "__main__":
    try:
        # [테스트 1]
        print_header("[테스트 1] TOP 5 카페 통합 리포트")
        result1 = recommend_top_5_desserts_tool.invoke({
            "region": "강남", "keyword": "카페",
            "persona_data": {"budget_level": "중", "interests": ["조용한"], "allergies": [], "is_diet_mode": False}
        })
        print(result1[:500] + "\n...(생략)...")

        # [테스트 2]
        print_header("[테스트 2] 카페 리스트 간단 검색")
        result2 = search_cafe_list_tool.invoke({"region": "홍대", "keyword": "디저트", "num_results": 3})
        if result2['success']:
            for cafe in result2['cafes']:
                print(f"[{cafe['순위']}] {cafe['이름']} | {cafe['평점']}")

        # [테스트 3]
        print_header("[테스트 3] 지역별 카페 가격 분석 (구체적 가격)")
        result3 = analyze_cafe_price_tool.invoke({"region": "성수동", "menu_type": "소금빵"})
        print(result3)
        
        print("\n✅ 모든 테스트 완료")

    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")