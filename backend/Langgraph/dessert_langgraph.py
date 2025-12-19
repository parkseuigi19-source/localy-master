"""Dessert/Cafe LangGraph Orchestrator - ReAct Agent"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# LLM을 함수로 변경 (lazy initialization)
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Dessert Tools import
from agents.tool.dessert_tool import (
    recommend_top_5_desserts_tool,
    search_cafe_list_tool,
    analyze_cafe_detail_tool,
    analyze_cafe_price_tool
)

# Tool 리스트 (4개)
tools = [
    recommend_top_5_desserts_tool,
    search_cafe_list_tool,
    analyze_cafe_detail_tool,
    analyze_cafe_price_tool
]

# System Prompt
system_prompt = """당신은 디저트/카페 추천 전문 AI입니다.

핵심 기능:
1. recommend_top_5_desserts_tool - TOP 5 카페 통합 리포트
2. search_cafe_list_tool - 카페 리스트 간단 검색
3. analyze_cafe_detail_tool - 특정 카페 상세 분석
4. analyze_cafe_price_tool - 지역별 카페 가격 분석

사용자 요청에 가장 적합한 tool을 선택하세요.
간결하고 유용한 정보를 제공하세요.
"""

# ReAct Agent 생성
_dessert_react_agent = create_react_agent(
    get_llm(),
    tools,
    state_modifier=system_prompt
)

# Wrapper: messages → final_response 변환
class DessertGraphWrapper:
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
        result = _dessert_react_agent.invoke({
            "messages": [("user", user_input)]
        })
        
        # 마지막 메시지 추출
        final_message = result["messages"][-1].content
        
        return {
            "final_response": final_message
        }

# Export
dessert_graph = DessertGraphWrapper()


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🍰 Dessert Agent 테스트")
    print("=" * 60)
    
    result = dessert_graph.invoke({
        "user_input": "홍대 카페 추천해줘"
    })
    
    print(f"\n응답: {result['final_response']}")
    print("\n완료!")
