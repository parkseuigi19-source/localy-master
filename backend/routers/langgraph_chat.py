from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re

from agents.coordinator import get_coordinator_response

router = APIRouter(
    prefix="/api/langgraph",
    tags=["langgraph"],
    responses={404: {"description": "Not found"}},
)


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []


class UIElement(BaseModel):
    """UI 요소 메타데이터"""
    type: str  # "calendar", "place_list", "map", "button"
    data: Dict[str, Any]


class ChatResponse(BaseModel):
    response: str  # AI 응답
    phase: str  # chat
    required_info_complete: bool
    ui_elements: Optional[List[UIElement]] = []  # UI 요소 리스트


@router.post("/chat", response_model=ChatResponse)
async def langgraph_chat(request: ChatRequest):
    """
    LangGraph Coordinator Agent 챗봇 엔드포인트
    - LLM이 자동으로 Agent 선택
    - Memory 기반 대화
    """
    try:
        print(f"\n=== Coordinator Agent 실행 ===")
        print(f"입력: {request.message}")
        
        # Coordinator Agent 호출
        response = get_coordinator_response(
            message=request.message,
            session_id="default"
        )
        
        print(f"응답: {response[:100]}...")
        
        # UI 요소 리스트
        ui_elements = []
        
        # 출발지 관련 질문이면 지하철역 검색 버튼 추가
        # "어디서 출발" 또는 "출발할 거냥" 포함 시 버튼 추가
        # 단, "몇 시에 출발"은 제외 (시간 질문)
        if ("어디서 출발" in response or "출발할 거냥" in response) and "몇 시" not in response:
            from agents.utils.button_formatter import create_button_ui
            
            subway_button = create_button_ui(
                text="🚇 지하철역 검색",
                action="subway_search"
            )
            ui_elements.append(subway_button)
            print(f"🚇 지하철역 검색 버튼 추가됨")
        
        # 시간 관련 질문이면 시간 선택 버튼 추가 (우선 체크)
        # 매우 엄격하게 매칭: 시간 관련 질문에만 반응
        time_keywords = ["몇 시에 출발", "출발 시간은", "출발 시각", "몇 시에 떠", "몇 시에 가"]
        # "몇 시" 단독으로는 사용 안 함 ("몇 시간" 같은 단어와 혼동 방지)
        if any(keyword in response for keyword in time_keywords):
            from agents.utils.button_formatter import create_button_ui
            
            button_ui = create_button_ui(
                text="⏰ 시간 선택",
                action="time_picker"
            )
            ui_elements.append(button_ui)
            print(f"⏰ 시간 선택 버튼 추가됨")
        # 날짜 관련 질문이면 달력 열기 버튼 추가 (시간 키워드가 없을 때만)
        # "언제" 단독으로는 사용 안 함 ("언제 1일차" 같은 질문과 혼동 방지)
        # 하지만 "언제 여행", "언제 가" 같은 패턴은 감지
        # 맛집/음식 관련 질문에는 절대 나타나지 않도록 함
        date_keywords = [
            "언제 출발", "언제 떠", "언제 가냥", "언제 갈", "언제 여행", "언제 가",
            "여행 날짜", "출발 날짜", "며칠부터", "몇월 몇일",
            "날짜 정해", "날짜 선택", "일정 정해", "일정 잡"
        ]
        # 맛집/음식 관련 키워드가 있으면 달력 버튼 표시 안 함
        food_keywords = ["맛집", "음식", "먹고", "식당", "레스토랑", "점심", "저녁", "아침"]
        has_food_keyword = any(keyword in response for keyword in food_keywords)
        
        if any(keyword in response for keyword in date_keywords) and not has_food_keyword:
            from agents.utils.button_formatter import create_button_ui
            
            button_ui = create_button_ui(
                text="📅 날짜 선택",
                action="calendar_open"
            )
            ui_elements.append(button_ui)
            print(f"👆 달력 열기 버튼 추가됨")
        
        # 장소 정보가 있으면 place_list UI 생성
        # 패턴: "🍟 **장소명**" 또는 "**5. 장소명**" 형식
        # 주의: "무슨 음식" 같은 질문에는 장소 카드를 생성하지 않음
        place_pattern = r'(?:\d+\.\s*)?(?:🍟|⭐|📍|🏨|☕|🍰)?\s*\*\*([^*]+)\*\*'
        places_found = re.findall(place_pattern, response)
        
        # 실제 장소 추천인지 확인 ("추천", "소개" 같은 단어가 있어야 함)
        is_recommendation = any(keyword in response for keyword in ["추천", "소개", "먹어봐", "가봐", "방문해봐"])
        
        if places_found and len(places_found) > 0 and is_recommendation:
            # 장소명 필터링: 평점(4.8점), 숫자만 있는 것, 너무 짧은 것 제외
            valid_places = []
            for place_name in places_found:  # 모든 매칭 결과를 필터링
                clean_name = place_name.strip()
                
                # 필터링 조건
                # 1. 평점 패턴 제외 (예: "4.8점", "5점")
                if re.match(r'^\d+\.?\d*점?$', clean_name):
                    print(f"⚠️ 평점으로 판단하여 제외: {clean_name}")
                    continue
                
                # 2. 숫자로 시작하는 패턴 제외 (예: "1.", "2)")
                if re.match(r'^\d+[\.\)]', clean_name):
                    print(f"⚠️ 번호 매기기로 판단하여 제외: {clean_name}")
                    continue
                
                # 3. 최소 2글자 이상의 한글 또는 영문이 포함되어야 함
                if not re.search(r'[가-힣]{2,}|[a-zA-Z]{2,}', clean_name):
                    print(f"⚠️ 유효한 장소명이 아님: {clean_name}")
                    continue
                
                # 4. 길이 체크 (1글자는 제외)
                if len(clean_name) <= 1:
                    continue
                
                valid_places.append(clean_name)
            
            # 필터링 후 최대 5개만 선택
            valid_places = valid_places[:5]
            
            # 유효한 장소가 없으면 UI 생성 안 함
            if not valid_places:
                print("⚠️ 유효한 장소명이 없어 place_list UI 생성 안 함")
            else:
                # 장소 정보를 추출하여 UI 요소 생성
                from agents.utils.ui_formatter import create_place_list_ui
                import googlemaps
                import os
                
                # Google Maps API 클라이언트 초기화
                gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
                
                # 응답에서 주소 정보도 추출 시도
                # 패턴: "주소: ...", "위치: ...", "주소지: ..." 등
                address_pattern = r'(?:주소|위치|Address)\s*[:|은|가]?\s*([^\n]+)'
                addresses = re.findall(address_pattern, response)

                
                # 간단한 장소 데이터 생성
                places_data = []
                for idx, clean_name in enumerate(valid_places):
                    # 해당 장소의 주소를 찾기 (응답에서 장소명 뒤에 주소가 있을 수 있음)
                    place_address = addresses[idx].strip() if idx < len(addresses) else "주소 정보 없음"
                    
                    # Google Geocoding API로 좌표 가져오기
                    lat, lng = 0, 0
                    try:
                        # 가게 이름 + 주소로 검색
                        search_query = f"{clean_name} {place_address}" if place_address != "주소 정보 없음" else clean_name
                        geocode_result = gmaps.geocode(search_query, language='ko')
                        
                        if geocode_result and len(geocode_result) > 0:
                            location = geocode_result[0]['geometry']['location']
                            lat = location['lat']
                            lng = location['lng']
                            # 주소가 없었으면 Geocoding 결과에서 가져오기
                            if place_address == "주소 정보 없음":
                                place_address = geocode_result[0].get('formatted_address', '주소 정보 없음')
                            print(f"✅ 좌표 찾음: {clean_name} → ({lat}, {lng})")
                        else:
                            print(f"⚠️ 좌표 못 찾음: {clean_name}")
                    except Exception as e:
                        print(f"❌ Geocoding 에러: {clean_name} - {e}")
                    
                    places_data.append({
                        "name": clean_name,
                        "address": place_address,
                        "lat": lat,
                        "lng": lng,
                        "tags": [],
                        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={clean_name.replace(' ', '+')}"
                    })
                
                if places_data:
                    place_list_ui = create_place_list_ui(
                        places=places_data,
                        title="추천 장소",
                        selection_mode="single"
                    )
                    ui_elements.append(place_list_ui)
                    print(f"📍 장소 카드 UI 추가됨: {len(places_data)}개")
                    for place in places_data:
                        print(f"  - {place['name']}: {place['address']}")
        
        # 결과 구성
        return ChatResponse(
            response=response,
            phase="chat",
            required_info_complete=True,
            ui_elements=ui_elements
        )
        
    except Exception as e:
        print(f"Coordinator 에러: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Coordinator 실행 실패: {str(e)}"
        )


@router.get("/health")
async def langgraph_health():
    """
    Coordinator Agent 시스템 헬스 체크
    """
    return {
        "status": "ok",
        "system": "coordinator_agent_pattern",
        "agents": ["restaurant", "dessert", "accommodation", "landmark", "region", "chat"],
        "architecture": "LangChain Coordinator + LangGraph Agents"
    }
