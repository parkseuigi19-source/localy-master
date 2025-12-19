"""디저트/카페 에이전트 - 최종 타임어택 버전 (완전 병렬 실행)"""
import os
import time
import logging
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import googlemaps
from langchain_openai import ChatOpenAI
from schemas.data_models import PlaceData, AgentResponse, UserPersona

# 1. 환경 설정
load_dotenv()
# 로깅 레벨을 WARNING으로 올려서 불필요한 출력으로 인한 딜레이 제거
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# 외부 라이브러리 로그 차단
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# --- [Helper] 페르소나 점수 계산 ---
def calculate_persona_score(place: dict, persona: Optional[UserPersona]) -> float:
    if not persona: return 0.5
    score = 0.5
    place_price = place.get('price_level', 2)
    budget_map = {"저": 1, "중": 2, "고": 3}
    persona_price = budget_map.get(persona.budget_level, 2)
    if place_price == persona_price: score += 0.3
    elif abs(place_price - persona_price) == 1: score += 0.15
    
    place_name = place.get('name', '').lower()
    interest_keywords = {
        '카페': ['cafe'], '사진': ['photo', 'view'], '조용': ['quiet', 'book'], 
        '맛집투어': ['dessert'], '다이어트': ['salad', 'healthy', '샐러드', '건강']
    }
    for interest in persona.interests:
        for kw in interest_keywords.get(interest, []):
            if kw in place_name: score += 0.1
    return min(score, 1.0)

# --- [Helper] 리뷰 품질 점수 계산 ---
def calculate_review_quality_score(place_dict: dict) -> float:
    import math
    rating = place_dict.get('rating', 0)
    review_count = place_dict.get('user_ratings_total', 0)
    rating_score = rating * 10
    review_score = min(30, math.log(review_count + 1) * 5)
    persona_score = place_dict.get('persona_score', 0.5) * 20
    return rating_score + review_score + persona_score

# --- [Step 1] 통합 검색 (초경량 모드) ---
def search_desserts_integrated(region: str, keyword: str, num_results: int = 5, persona: Optional[UserPersona] = None) -> AgentResponse:
    try:
        # 0. Serper 웹 검색 (2단계 전략)
        place_names_from_web = []
        try:
            from agents.utils.serper_utils import search_with_serper, extract_place_names
            
            # 1차: 메뉴 특화 검색 (사용자 입력 그대로)
            if keyword:
                search_query_specific = f"{region} {keyword}"
                logger.warning(f"🌐 Serper 1차 검색 (메뉴 특화): {search_query_specific}")
                serper_results = search_with_serper(search_query_specific, num_results=10)
                
                if serper_results:
                    place_names_from_web = extract_place_names(serper_results, keyword)
                    logger.warning(f"📝 1차 검색 결과: {len(place_names_from_web)}개")
                
                # 2차: 일반 검색 (결과가 부족하면)
                if len(place_names_from_web) < 5:
                    # 메뉴에서 카테고리 추출 (예: "딸기 케이크" → "케이크")
                    general_category = keyword.split()[-1] if ' ' in keyword else keyword
                    
                    if general_category != keyword:  # 메뉴 특화와 다른 경우만
                        search_query_general = f"{region} {general_category}"
                        logger.warning(f"🌐 Serper 2차 검색 (일반): {search_query_general}")
                        serper_results_2 = search_with_serper(search_query_general, num_results=10)
                        
                        if serper_results_2:
                            additional_names = extract_place_names(serper_results_2, general_category)
                            # 중복 제거하고 추가
                            for name in additional_names:
                                if name not in place_names_from_web:
                                    place_names_from_web.append(name)
                            logger.warning(f"📝 2차 검색 추가: {len(additional_names)}개 (총 {len(place_names_from_web)}개)")
        except Exception as e:
            logger.warning(f"⚠️ Serper 검색 실패 (Google Places만 사용): {e}")
        
        geocode = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode: return AgentResponse(success=False, message="지역 찾기 실패")
        coords = geocode[0]['geometry']['location']
        
        # [최적화] 반경 1.5km로 축소하여 데이터 스캔 속도 향상
        first_page = gmaps.places_nearby(
            location=(coords['lat'], coords['lng']), 
            radius=1500, 
            type="cafe", 
            keyword=keyword, 
            language="ko"
        )
        # 페이지네이션 로직 완전 제거 (첫 페이지 20개로 승부)
        raw_results = first_page.get('results', [])
        
        filtered = [r for r in raw_results if r.get('user_ratings_total', 0) >= 10]
        
        for p in filtered:
            p['persona_score'] = calculate_persona_score(p, persona)
            p['quality_score'] = calculate_review_quality_score(p)
        
        sorted_results = sorted(filtered, key=lambda x: x.get('quality_score', 0), reverse=True)
        
        # 다양성을 위한 랜덤 셔플 (상위 15개 중에서)
        import random
        top_candidates = sorted_results[:15]  # 상위 15개
        random.shuffle(top_candidates)  # 랜덤 섞기
        final_results = top_candidates[:num_results]  # num_results 개 선택
        
        logger.warning(f"🎯 랜덤 선택: {len(final_results)}개")
        
        final_places = []
        for p in final_results:
            final_places.append(PlaceData(
                place_id=p['place_id'], 
                name=p['name'], 
                category="cafe",
                address=p.get('vicinity', ''), 
                latitude=p['geometry']['location']['lat'], 
                longitude=p['geometry']['location']['lng'],
                region=region, 
                rating=p.get('rating', 0), 
                review_count=p.get('user_ratings_total', 0), 
                price_level=p.get('price_level', 0),
                tags=[], 
                google_maps_url=f"https://www.google.com/maps/place/?q=place_id:{p['place_id']}"
            ))
        
        return AgentResponse(
            success=True, 
            agent_name="dessert_search", 
            data=[p.model_dump() for p in final_places], 
            count=len(final_places), 
            message=f"TOP {len(final_places)}개 선정 완료"
        )
    except Exception as e:
        return AgentResponse(success=False, message="검색 오류", error=str(e))

# --- [Step 2] 리포트 생성 ---
def generate_korean_ux_report(place_id: str, persona: Optional[UserPersona] = None) -> AgentResponse:
    try:
        # [최적화] 리뷰 필드만 딱 가져옴
        details = gmaps.place(place_id, fields=['name', 'rating', 'formatted_address', 'reviews'], language="ko")
        result = details['result']
        reviews = result.get('reviews', [])[:10] # [최적화] 리뷰 10개만 분석 (충분함)
        
        if not reviews: return AgentResponse(success=False, message="리뷰 부족")
        
        review_text = "\n".join([r['text'] for r in reviews])
        
        # [최적화] LLM 입력 데이터 길이 제한 (토큰 절약 = 속도 향상)
        if len(review_text) > 1500:
            review_text = review_text[:1500]

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        
        prompt_full = f"""당신은 카페 가이드 AI입니다. 
아래 정보를 바탕으로 사용자에게 추천하는 짧고 강렬한 리포트를 작성하세요.

카페명: {result.get('name')}
평점: {result.get('rating')}
리뷰: {review_text}

형식:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ☕ {{카페명}} (⭐ {{평점}})
┃  📍 {{주소}}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

💬 한줄평: {{핵심 매력}}

🏷️ 태그: {{태그 3개}}

🍰 추천 메뉴 (가격 포함):
1. {{메뉴}}
2. {{메뉴}}
3. {{메뉴}}

📊 요약:
• 분위기: {{내용}}
• 장점: {{내용}}
• 단점: {{내용}}

🎯 추천 이유: {{내용}}
"""
        response = llm.invoke(prompt_full)
        
        return AgentResponse(
            success=True, 
            agent_name="dessert_ux_report", 
            message="리포트 생성 완료", 
            data=[{
                "place_id": place_id,
                "place_name": result.get('name'),
                "formatted_report": response.content
            }]
        )

    except Exception as e:
        return AgentResponse(success=False, message="리포트 생성 실패", error=str(e))


# --- [Step 3] 가격 정보 분석 (극한 최적화) ---
def get_cafe_price_analysis(region: str, menu_type: str = "커피", persona: Optional[UserPersona] = None) -> AgentResponse:
    try:
        geocode = gmaps.geocode(f"{region}, 대한민국", language="ko")
        coords = geocode[0]['geometry']['location']
        
        # [최적화] 5개만 검색
        first_page = gmaps.places_nearby(
            location=(coords['lat'], coords['lng']),
            radius=1500,
            type="cafe",
            keyword=f"{menu_type} 맛집",
            language="ko"
        )
        raw_results = first_page.get('results', [])[:5] 
        
        all_menu_mentions = []
        
        def fetch_place_detail(place):
            try:
                # [최적화] 리뷰만 가져옴
                res = gmaps.place(place['place_id'], fields=['reviews'], language="ko")
                return res.get('result', {})
            except:
                return None

        # [최적화] 동시 실행
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_place_detail, p) for p in raw_results]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    # [최적화] 각 카페당 리뷰 5개만 확인
                    reviews = result.get('reviews', [])[:5]
                    for review in reviews:
                        all_menu_mentions.append(review.get('text', ''))
        
        combined_reviews = "\n".join(all_menu_mentions)
        
        # [최적화] 입력 텍스트 1500자로 제한 (LLM 속도 핵심)
        if len(combined_reviews) > 1500:
            combined_reviews = combined_reviews[:1500]
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        
        prompt_full = f"""지역: {region}, 메뉴: {menu_type}
리뷰 데이터를 보고 가격 정보를 숫자(원)로 정확히 요약하세요.

리뷰: {combined_reviews}

형식:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💰 {region} {menu_type} 가격 정보
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📊 평균 가격: 아메리카노 {{최저~최고}}원, 디저트 {{최저~최고}}원

🔥 인기 메뉴 TOP 3:
1️⃣ {{메뉴}} ({{가격}})
2️⃣ {{메뉴}} ({{가격}})
3️⃣ {{메뉴}} ({{가격}})

💡 팁: {{내용}}
"""
        response = llm.invoke(prompt_full)
        
        return AgentResponse(
            success=True,
            agent_name="cafe_price_analysis",
            message="가격 분석 완료",
            data=[{
                "region": region,
                "menu_type": menu_type,
                "price_report": response.content
            }]
        )
        
    except Exception as e:
        return AgentResponse(success=False, message="가격 분석 오류", error=str(e))

# ==========================================================
# 🔥 병렬 테스트 (진짜 속도 향상의 핵심)
# ==========================================================
def run_search_and_report_task(region, keyword, persona):
    """검색과 리포트 생성을 담당하는 작업"""
    print("   [작업1] 카페 검색 시작...")
    search_res = search_desserts_integrated(region, keyword, num_results=5, persona=persona)
    
    report_output = ""
    list_output = ""
    
    if search_res.success and search_res.data:
        # 리스트 출력 준비
        list_output += f"\n{'='*40}\n검색된 카페: {len(search_res.data)}개\n{'='*40}\n"
        for i, place in enumerate(search_res.data, 1):
            list_output += f"[{i}] {place['name']} (⭐{place['rating']})\n"

        # 상세 리포트 생성
        print("   [작업1] 상세 리포트 생성 중...")
        report_res = generate_korean_ux_report(search_res.data[0]['place_id'], persona=persona)
        if report_res.success:
            report_output = report_res.data[0]['formatted_report']
        else:
            report_output = "리포트 생성 실패"
    else:
        list_output = "검색 실패"
        
    return list_output, report_output

def run_price_analysis_task(region, menu_type, persona):
    """가격 분석을 담당하는 작업"""
    print("   [작업2] 가격 정보 분석 시작...")
    price_res = get_cafe_price_analysis(region, menu_type, persona=persona)
    if price_res.success:
        return price_res.data[0]['price_report']
    return "가격 분석 실패"

if __name__ == "__main__":
    start_time = time.time()
    
    print("\n🚀 [초고속 모드] 디저트 에이전트 실행\n")
    
    test_persona = UserPersona(
        budget_level="중", interests=["조용한"], allergies=[], is_diet_mode=False
    )
    REGION = "부산"

    # 🔥 핵심: 두 작업을 동시에 실행 (ThreadPoolExecutor)
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 작업 1: 검색 + 리포트
        future1 = executor.submit(run_search_and_report_task, REGION, "카페", test_persona)
        # 작업 2: 가격 분석 (검색 결과 안 기다리고 바로 시작)
        future2 = executor.submit(run_price_analysis_task, REGION, "디저트", test_persona)
        
        # 결과 대기
        list_out, report_out = future1.result()
        price_out = future2.result()

    # 결과 일괄 출력
    print("\n" + "=" * 60)
    print("[결과 1] 검색 리스트")
    print(list_out)
    
    print("\n" + "=" * 60)
    print("[결과 2] 상세 리포트")
    print(report_out)
    
    print("\n" + "=" * 60)
    print("[결과 3] 가격 분석")
    print(price_out)

    end_time = time.time()
    print(f"\n⚡ 총 실행 시간: {round(end_time - start_time, 2)}초")