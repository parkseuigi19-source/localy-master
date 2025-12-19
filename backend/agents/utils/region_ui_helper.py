"""
Region Agent 출력을 UI 형식으로 변환하는 헬퍼 함수
"""

from agents.region_agent import recommend_regions
from agents.utils.ui_formatter import create_place_list_ui, format_place_for_ui


def get_region_recommendations_with_ui(destination: str) -> dict:
    """
    Region Agent를 호출하고 UI 형식으로 변환
    
    Args:
        destination: 목적지 (예: "부산")
    
    Returns:
        dict: {
            "text_response": str,  # LLM 텍스트 응답
            "ui_elements": list    # UI 요소 리스트
        }
    """
    # Region Agent 호출
    result = recommend_regions(destination)
    
    if not result.success or not result.data:
        return {
            "text_response": f"{destination}에 대한 지역 정보를 찾지 못했어냥... 😿",
            "ui_elements": []
        }
    
    # 장소 데이터를 UI 형식으로 변환
    ui_places = []
    for region in result.data:
        # Region Agent의 데이터를 PlaceData 형식으로 변환
        # Region Agent는 좌표를 제공하지 않으므로 Google Maps 검색 URL만 사용
        ui_place = {
            "name": region.get("name", ""),
            "address": region.get("description", ""),  # description을 address로 사용
            "lat": 0,  # 좌표 없음 (검색 URL로 대체)
            "lng": 0,
            "tags": region.get("tags", []),
            "google_maps_url": region.get("google_maps_url", "")
        }
        ui_places.append(ui_place)
    
    # UI 요소 생성
    ui_element = create_place_list_ui(
        places=ui_places,
        title=f"{destination} 지역의 추천 여행지",
        selection_mode="multiple"  # 여러 개 선택 가능
    )
    
    # 텍스트 응답
    text_response = f"{destination}이냥! 🐾 어디 가볼까냥?\n마음에 드는 곳 **다 골라도** 된다냥! 😸"
    
    return {
        "text_response": text_response,
        "ui_elements": [ui_element]
    }


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("Region Agent UI 변환 테스트")
    print("=" * 60)
    
    result = get_region_recommendations_with_ui("부산")
    
    print(f"\n텍스트 응답:\n{result['text_response']}")
    print(f"\nUI 요소 개수: {len(result['ui_elements'])}")
    
    if result['ui_elements']:
        import json
        print(f"\nUI 요소 (JSON):")
        print(json.dumps(result['ui_elements'][0], ensure_ascii=False, indent=2))
