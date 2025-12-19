"""Accommodation LangGraph Orchestrator - ReAct Agent"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# LLM을 함수로 변경 (lazy initialization)
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Accommodation Tools import
from agents.tool.accommodation_tools import (
    search_accommodations,
    summarize_reviews,
    compare_booking_prices,
    get_recommended_accommodations
)

# Tool 리스트
tools = [
    search_accommodations,
    summarize_reviews,
    compare_booking_prices,
    get_recommended_accommodations
]

# System Prompt
system_prompt = """당신은 숙소 추천 전문 AI입니다.

핵심 기능:
1. search_accommodations - 숙소 검색
2. summarize_reviews - AI 리뷰 요약
3. compare_booking_prices - 가격 비교
4. get_recommended_accommodations - AI 추천

사용자 요청에 가장 적합한 tool을 선택하세요.
간결하고 유용한 정보를 제공하세요.
"""

# ReAct Agent 생성
_accommodation_react_agent = create_react_agent(
    get_llm(),
    tools,
    state_modifier=system_prompt
)

# Wrapper: messages → final_response 변환
class AccommodationGraphWrapper:
    """Coordinator와 호환되도록 State 변환"""
    
    def invoke(self, state: dict) -> dict:
        """
        Args:
            state: {"user_input": str}
        Returns:
            {"final_response": str}
        """
        user_input = state.get("user_input", "")
        
        # ReAct Agent 호출
        result = _accommodation_react_agent.invoke({
            "messages": [("user", user_input)]
        })
        
        # 마지막 메시지 추출
        final_message = result["messages"][-1].content
        
        return {
            "final_response": final_message
        }

# Export
accommodation_graph = AccommodationGraphWrapper()


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🏨 Accommodation Agent 테스트")
    print("=" * 60)
    
    result = accommodation_graph.invoke({
        "user_input": "제주도 호텔 추천해줘"
    })
    
    print(f"\n응답: {result['final_response']}")
    print("\n완료!")
