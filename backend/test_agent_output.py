"""
에이전트 출력 테스트 스크립트
실제 에이전트를 호출하여 장소 데이터를 가져오고 UI 형식으로 변환
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.restaurant_agent import search_restaurants
from agents.utils.ui_formatter import format_places_for_ui, create_place_list_ui
import json


def test_restaurant_agent():
    """맛집 에이전트 테스트"""
    print("=" * 60)
    print("맛집 에이전트 테스트")
    print("=" * 60)
    
    # 맛집 검색
    result = search_restaurants(
        region="부산 해운대",
        preference="일식",
        num_results=5
    )
    
    print(f"\n✅ 검색 성공: {result.success}")
    print(f"📊 결과 개수: {result.count}")
    print(f"💬 메시지: {result.message}")
    
    if result.success and result.data:
        print(f"\n📍 찾은 맛집:")
        for i, place in enumerate(result.data[:3], 1):
            print(f"\n{i}. {place['name']}")
            print(f"   주소: {place['address']}")
            print(f"   평점: {place.get('rating', 'N/A')} ⭐")
            print(f"   리뷰: {place.get('review_count', 'N/A')}개")
        
        # UI 형식으로 변환
        print("\n" + "=" * 60)
        print("UI 형식 변환")
        print("=" * 60)
        
        ui_places = format_places_for_ui(result.data)
        ui_element = create_place_list_ui(
            places=ui_places,
            title="부산 해운대 일식 맛집",
            selection_mode="single"
        )
        
        print("\n📦 UI 요소:")
        print(json.dumps(ui_element, ensure_ascii=False, indent=2))
        
        return ui_element
    else:
        print(f"\n❌ 에러: {result.error}")
        return None


def test_region_recommendations():
    """지역 추천 테스트 (실제 Region Agent 사용)"""
    print("\n" + "=" * 60)
    print("지역 추천 테스트 (Region Agent)")
    print("=" * 60)
    
    from agents.utils.region_ui_helper import get_region_recommendations_with_ui
    
    # Region Agent 호출 및 UI 변환
    result = get_region_recommendations_with_ui("부산")
    
    print(f"\n텍스트 응답:\n{result['text_response']}")
    print(f"\nUI 요소 개수: {len(result['ui_elements'])}")
    
    if result['ui_elements']:
        ui_element = result['ui_elements'][0]
        print(f"\n📦 UI 요소:")
        print(json.dumps(ui_element, ensure_ascii=False, indent=2))
        
        # 장소 개수 확인
        places_count = len(ui_element['data']['places'])
        print(f"\n✅ 총 {places_count}개 장소 반환됨")
        
        return ui_element
    else:
        print("\n❌ UI 요소 없음")
        return None


def test_full_response():
    """전체 응답 형식 테스트"""
    print("\n" + "=" * 60)
    print("전체 응답 형식 테스트")
    print("=" * 60)
    
    # 맛집 UI 요소
    restaurant_result = search_restaurants(
        region="부산 해운대",
        preference="일식",
        num_results=3
    )
    
    ui_elements = []
    
    if restaurant_result.success and restaurant_result.data:
        ui_places = format_places_for_ui(restaurant_result.data)
        place_list_ui = create_place_list_ui(
            places=ui_places,
            title="부산 해운대 일식 맛집",
            selection_mode="single"
        )
        ui_elements.append(place_list_ui)
    
    # 전체 응답 구성
    full_response = {
        "response": "부산 해운대에서 일식 맛집을 찾았어냥! 🍣\n이 중에서 1개만 골라달라냥! 😸",
        "phase": "chat",
        "required_info_complete": False,
        "ui_elements": ui_elements
    }
    
    print("\n📦 전체 응답:")
    print(json.dumps(full_response, ensure_ascii=False, indent=2))
    
    return full_response


if __name__ == "__main__":
    print("\n🚀 에이전트 출력 테스트 시작\n")
    
    # 1. 맛집 에이전트 테스트
    restaurant_ui = test_restaurant_agent()
    
    # 2. 지역 추천 테스트
    region_ui = test_region_recommendations()
    
    # 3. 전체 응답 형식 테스트
    full_response = test_full_response()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)
