"""Restaurant LangGraph Orchestrator - ReAct Agent"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# LLM을 함수로 변경 (lazy initialization)
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 핵심 Tool만 (5개)
from agents.tool.restaurant_tools import (
    search_restaurants_tool,
    extract_menu_tool,
    get_restaurant_reviews_tool,
    verify_restaurant_tool,
    get_restaurant_details_tool
)

# Tool 리스트 (5개)
tools = [
    search_restaurants_tool,
    extract_menu_tool,
    get_restaurant_reviews_tool,
    verify_restaurant_tool,
    get_restaurant_details_tool
]

# System Prompt (고도화 - 페르소나 기반 스마트 추천)
system_prompt = """당신은 맛집 추천 전문 AI입니다.

**핵심 원칙:**
1. Tool 결과는 절대 수정하지 말고 그대로 전달
2. Tool 결과 앞뒤로 짧은 인사말만 추가 가능
3. 사용자 의도를 정확히 파악하여 적절한 파라미터 설정

**페르소나 기반 스마트 추천 로직:**

**20대 여성 + 데이트/기념일:**
- preference="분위기 좋은 레스토랑" 또는 "SNS 핫플" 또는 "브런치"
- 특징: 인스타그램 감성, 예쁜 플레이팅, 분위기 중시
- 제외: 본죽, 도미노피자, 버거킹 등 체인점
- 예: 파스타, 브런치 카페, 디저트 맛집

**20대 남성 + 친구/데이트:**
- preference="고기" 또는 "술집" 또는 "라멘"
- 특징: 양 많고, 가성비, 술 잘 어울림
- 예: 삼겹살, 치킨, 포차, 라멘

**30대 직장인 + 회식:**
- preference="회식" 또는 "고기" 또는 "술집"
- 특징: 단체석, 주차 가능, 술 종류 다양
- 예: 삼겹살, 곱창, 고깃집

**가족 여행 (아이 동반):**
- preference="가족 맛집" 또는 "아이 동반"
- 특징: 넓은 좌석, 아이 메뉴, 조용함
- 예: 한식당, 뷔페, 패밀리 레스토랑

**혼자 식사:**
- preference="혼밥" 또는 "1인 식사"
- 특징: 빠른 서빙, 1인석, 가성비
- 예: 라멘, 덮밥, 국밥

**Tool 사용 가이드:**
- search_restaurants_tool: 맛집 검색 (지역, 카테고리, 선호도)
- extract_menu_tool: 메뉴 정보 추출
- get_restaurant_reviews_tool: 리뷰 분석
- verify_restaurant_tool: 신뢰도 검증
- get_restaurant_details_tool: 상세 정보 (예약/가격/주차)

**응답 스타일:**
- 친근하고 자연스럽게
- Tool 결과는 그대로 전달
- 짧은 인사말로 시작/마무리 OK
"""

# ReAct Agent 생성
_restaurant_react_agent = create_react_agent(
    get_llm(),  # Lazy initialization
    tools,
    state_modifier=system_prompt
)

# Wrapper: messages → final_response 변환
class RestaurantGraphWrapper:
    """Coordinator와 호환되도록 State 변환"""
    
    def invoke(self, state: dict) -> dict:
        """
        Args:
            state: {"user_input": str}
        Returns:
            {"final_response": str}
        """
        user_input = state.get("user_input", "")
        
        # ReAct Agent 호출 (messages 형식)
        result = _restaurant_react_agent.invoke({
            "messages": [("user", user_input)]
        })
        
        # 마지막 메시지 추출
        final_message = result["messages"][-1].content
        
        return {
            "final_response": final_message
        }

# Export
restaurant_graph = RestaurantGraphWrapper()


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🍽️ Restaurant ReAct Agent 테스트")
    print("=" * 60)
    
    # 테스트 1: 검색
    print("\n테스트 1: 맛집 검색")
    result = restaurant_graph.invoke({
        "user_input": "서울 강남역 맛집 3개 찾아줘"
    })
    print(f"결과: {result['final_response']}")
    
    print("\n완료!")
