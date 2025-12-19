"""Landmark LangGraph Orchestrator - ReAct Agent"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# LLM을 함수로 변경 (lazy initialization)
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Landmark Agent 함수들을 Tool로 변환
from langchain.tools import tool
from agents.landmark_agent import (
    search_landmarks,
    get_landmark_detail,
    find_nearby_landmarks,
    recommend_by_season,
    recommend_by_time
)

@tool
def search_landmarks_tool(region: str, category: str = None, num_results: int = 5) -> dict:
    """관광지 검색
    
    Args:
        region: 지역명 (예: "서울 강남", "부산 해운대")
        category: 카테고리 (선택)
        num_results: 결과 개수
    """
    result = search_landmarks(region, category, num_results)
    return result.dict()

@tool
def get_landmark_detail_tool(place_name: str, region: str) -> dict:
    """관광지 상세 정보
    
    Args:
        place_name: 장소명
        region: 지역명
    """
    result = get_landmark_detail(place_name, region)
    return result.dict()

@tool
def find_nearby_landmarks_tool(place_name: str, region: str, radius: int = 3000) -> dict:
    """주변 관광지 찾기
    
    Args:
        place_name: 기준 장소명
        region: 지역명
        radius: 반경 (미터)
    """
    result = find_nearby_landmarks(place_name, region, radius)
    return result.dict()

@tool
def recommend_by_season_tool(region: str, season: str, num_results: int = 5) -> dict:
    """계절별 추천
    
    Args:
        region: 지역명
        season: 계절 (봄/여름/가을/겨울)
        num_results: 결과 개수
    """
    result = recommend_by_season(region, season, num_results)
    return result.dict()

@tool
def recommend_by_time_tool(region: str, time_of_day: str, num_results: int = 5) -> dict:
    """시간대별 추천
    
    Args:
        region: 지역명
        time_of_day: 시간대 (아침/오전/오후/저녁/밤)
        num_results: 결과 개수
    """
    result = recommend_by_time(region, time_of_day, num_results)
    return result.dict()

# Tool 리스트
tools = [
    search_landmarks_tool,
    get_landmark_detail_tool,
    find_nearby_landmarks_tool,
    recommend_by_season_tool,
    recommend_by_time_tool
]

# System Prompt
system_prompt = """당신은 관광지 추천 전문 AI입니다.

핵심 기능:
1. search_landmarks_tool - 관광지 검색
2. get_landmark_detail_tool - 상세 정보
3. find_nearby_landmarks_tool - 주변 관광지
4. recommend_by_season_tool - 계절별 추천
5. recommend_by_time_tool - 시간대별 추천

사용자 요청에 가장 적합한 tool을 선택하세요.
간결하고 유용한 정보를 제공하세요.
"""

# ReAct Agent 생성
_landmark_react_agent = create_react_agent(
    get_llm(),
    tools,
    state_modifier=system_prompt
)

# Wrapper: messages → final_response 변환
class LandmarkGraphWrapper:
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
        result = _landmark_react_agent.invoke({
            "messages": [("user", user_input)]
        })
        
        # 마지막 메시지 추출
        final_message = result["messages"][-1].content
        
        return {
            "final_response": final_message
        }

# Export
landmark_graph = LandmarkGraphWrapper()


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🏛️ Landmark Agent 테스트")
    print("=" * 60)
    
    result = landmark_graph.invoke({
        "user_input": "서울 관광지 추천해줘"
    })
    
    print(f"\n응답: {result['final_response']}")
    print("\n완료!")
