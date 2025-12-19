"""Shopping Places Finder Agent - Google Places API 활용"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool


# 프로젝트 루트를 Python 경로에 추가 (직접 실행 시)
if __name__ == "__main__":
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_dir))

# Tools 가져오기
try:
    # 검색 관련
    from tools.shopping_search_tool import (
        search_shopping_tool,
        has_category_keyword,
        search_shopping_by_coords,
    )
    # 추천 관련
    from tools.shopping_recommend_tool import (
        recommend_shopping_tool,
    )
except ImportError:
    # 직접 실행 시 경로 문제 보정
    sys.path.append(str(Path(__file__).parent.parent))
    from tools.shopping_search_tool import (
        search_shopping_tool,
        has_category_keyword,
    )
    from tools.shopping_recommend_tool import (
        recommend_shopping_tool,
    )

load_dotenv()

from typing import TypedDict, List, Dict, Any

class TravelAgentState(TypedDict):
    user_input: str
    destination: str
    shopping_results: List[Dict[str, Any]] | None
    final_response: str | None

# Google Maps API 키 (shopping_tools에서 사용되지만, 여기서는 키 존재 여부 확인용)
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

@tool
def current_location_shopping_tool(
    lat: float,
    lng: float,
    user_input: str,
) -> Dict[str, Any]:
    """
    [현재 위치용 통합 Tool]

    - 위도/경도(lat, lng) 기준으로 주변 쇼핑 장소를 검색하고
    - 평점/리뷰/카테고리를 고려해 GPT 추천 메시지까지 생성한다.

    반환 형식:
    {
        "user_input": str,
        "region": "현재 위치 근처",
        "shopping_results": [ place dict ... ],
        "final_response": str (추천 멘트)
    }
    """
    region_label = "현재 위치 근처"

    # 1) 카테고리/상품 키워드가 전혀 없으면 추가 질문
    if not has_category_keyword(user_input):
        return {
            "user_input": user_input,
            "region": region_label,
            "shopping_results": [],
            "final_response": (
                "어떤 종류의 쇼핑 장소를 찾으시나요? 🛍️\n\n"
                "예: '편의점', '대형마트', '다이소', '약국' 등으로 검색해주세요."
            ),
        }

    # 2) 현재 위치 기준으로 장소 검색
    shopping_places = search_shopping_by_coords(lat, lng, user_input)

    if not shopping_places:
        return {
            "user_input": user_input,
            "region": region_label,
            "shopping_results": [],
            "final_response": "현재 위치 근처에서 조건에 맞는 쇼핑 장소를 찾지 못했습니다. 😢",
        }

    # 3) 추천 메시지 생성 (기존 recommend_shopping_tool 재사용)
    recommendation = recommend_shopping_tool.invoke(
        {
            "region": region_label,
            "user_input": user_input,
            "shopping_places": shopping_places,
        }
    )

    return {
        "user_input": user_input,
        "region": region_label,
        "shopping_results": shopping_places,
        "final_response": recommendation,
    }

def shopping_agent_node(state: TravelAgentState) -> TravelAgentState:
    """
    쇼핑 장소 추천 에이전트

    - tools.shopping_search_tool.search_shopping_tool
    - tools.shopping_recommend_tool.recommend_shopping_tool
    를 사용해 검색 및 추천을 수행한다.
    """
    user_input = state["user_input"]
    destination = state.get("destination")
    
    # 1. destination 확인
    if not destination:
        return {
            "user_input": user_input,
            "destination": destination or "",
            "shopping_results": [],
            "final_response": "여행 목적지가 설정되지 않았습니다. 먼저 여행 계획을 세워주세요! ️",
        }
    
    region = destination
    
    # 2. 카테고리가 없으면 안내 메시지
    if not has_category_keyword(user_input):
        return {
            "user_input": user_input,
            "destination": region,
            "shopping_results": [],
            "final_response": (
                f"{region}에서 어떤 종류의 쇼핑 장소를 찾으시나요? 🛍️\n\n"
                "예: '편의점', '대형마트', '다이소', '약국' 등으로 검색해주세요."
            ),
        }
    
    # 3. 쇼핑 장소 검색 (Search Tool 사용)
    # LangChain Tool로 변경되었으므로 .invoke() 사용
    shopping_places = search_shopping_tool.invoke(
        {"region": region, "user_input": user_input}
    )
    
    if not shopping_places:
        return {
            "user_input": user_input,
            "destination": region,
            "shopping_results": [],
            "final_response": f"{region}에서 쇼핑 장소를 찾지 못했습니다. 다른 지역을 시도해보세요. 😢",
        }
    
    # 4. 추천 메시지 생성 (Recommendation Tool 사용)
    recommendation = recommend_shopping_tool.invoke(
        {"region": region, "user_input": user_input, "shopping_places": shopping_places}
    )
    
    print(f"[Shopping Agent] 추천 완료")
    
    return {
        "user_input": user_input,
        "destination": region,
        "shopping_results": shopping_places,
        "final_response": recommendation,
    }



# 테스트 - 하드코딩된 테스트 케이스
if __name__ == "__main__":
    print("=" * 50)
    print("🛍️  쇼핑 장소 추천 에이전트 테스트")
    print("=" * 50)
    
    if not GOOGLE_API_KEY:
        print("\n⚠️  경고: GOOGLE_PLACES_API_KEY가 설정되지 않았습니다!")
        print("📝 .env 파일에 API 키를 추가해주세요.")
        exit()
    
    # 테스트 케이스 (하드코딩)
    test_cases = [
        {"destination": "하남", "user_input": "편의점"},
        {"destination": "뚝섬", "user_input": "대형마트"},
        {"destination": "잠실", "user_input": "다이소"},
        {"destination": "해운대", "user_input": "고기 살만한 곳 알려줘"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        destination = test_case["destination"]
        user_input = test_case["user_input"]
        
        print(f"\n{'=' * 50}")
        print(f"테스트 #{i}: {destination}에서 {user_input} 검색")
        print("=" * 50)
        
        test_state = {
            "user_input": user_input,
            "destination": destination
        }
        
        result = shopping_agent_node(test_state)
        
        # 결과 출력
        if result.get('shopping_results'):
            all_places = result['shopping_results']

            # ✅ 평점 + 리뷰 수 기준으로 상위 5개만 추천 목록으로 사용
            sorted_places = sorted(
                all_places,
                key=lambda s: (
                    float(s.get("rating", 0) or 0),
                    int(s.get("review_count", 0) or 0),
                ),
                reverse=True,
            )
            top_places = sorted_places[:5]

            print(f"\n✅ 추천 장소(상위 5개): {len(top_places)}개")
            print("\n📋 추천 목록:")
            for j, place in enumerate(top_places, 1):
                print(f"  {j}. {place['name']}")
                print(f"     ⭐ {place['rating']} ({place['review_count']}개 리뷰)")
                print(f"     📍 {place['address']}")
                print(f"     🔗 지도: {place.get('map_url', '')}")

        print(f"\n💬 추천:\n{result['final_response']}")

        print("\n" + "-" * 50)
    
    print("\n✅ 모든 테스트 완료!")

    # ==============================
    # 2) 현재 위치 기반 툴 테스트
    # ==============================
    print("\n\n" + "=" * 50)
    print("현재 위치 기반 쇼핑 추천 테스트")
    print("=" * 50)

    # 🔥 테스트용 좌표 (예: 해운대역 근처) - 실제로는 네 위치 넣어도 됨
    current_lat = 35.158697
    current_lng = 129.160384
    current_user_input = "고기 살만한 곳 알려줘"

    print(f"\n[현재 위치] lat={current_lat}, lng={current_lng}")
    print(f"[현재 위치] user_input='{current_user_input}'")

    current_result = current_location_shopping_tool.invoke({
        "lat": current_lat,
        "lng": current_lng,
        "user_input": current_user_input,
    })

    # 결과 출력 (상위 5개만)
    places = current_result.get("shopping_results", [])
    if places:
        # 평점 + 리뷰수 기준 상위 5개
        sorted_places = sorted(
            places,
            key=lambda s: (
                float(s.get("rating", 0) or 0),
                int(s.get("review_count", 0) or 0),
            ),
            reverse=True,
        )
        top_places = sorted_places[:5]

        print(f"\n✅ 현재 위치 기준 추천 장소(상위 5개): {len(top_places)}개")
        print("\n📋 추천 목록:")
        for j, place in enumerate(top_places, 1):
            print(f"  {j}. {place['name']}")
            print(f"     ⭐ {place['rating']} ({place['review_count']}개 리뷰)")
            print(f"     📍 {place['address']}")
            print(f"     🔗 지도: {place.get('map_url', '')}")
    else:
        print("\n❌ 현재 위치 근처에서 검색 결과가 없습니다.")

    print(f"\n💬 추천 멘트:\n{current_result.get('final_response', '')}")
