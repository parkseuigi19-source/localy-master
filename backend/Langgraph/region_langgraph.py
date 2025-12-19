"""Region LangGraph Orchestrator"""
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# LLM을 함수로 변경 (lazy initialization)
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


class RegionState(TypedDict):
    """Region LangGraph 상태"""
    user_input: str
    intent: str  # "recommend", "attraction", "best_time", "popular"
    destination: Optional[str]
    travel_style: Optional[str]
    result: dict
    final_response: str


def classify_intent(state: RegionState) -> RegionState:
    """
    사용자 의도 파악 + 목적지 추출
    
    - "recommend": 특정 도시의 지역 추천
    - "attraction": 명소 검색
    - "best_time": 최적 방문 시기
    - "popular": 인기 여행지 추천
    """
    user_input = state["user_input"]
    
    # 의도 파악
    prompt = f"""다음 사용자 입력의 의도를 파악하세요:

"{user_input}"

다음 중 하나로 분류:
- recommend: 특정 도시의 세부 지역을 추천받고 싶음 (예: "부산 어디 가면 좋아?", "춘천갈래")
- attraction: 특정 지역의 명소를 알고 싶음 (예: "강릉 명소 알려줘")
- best_time: 특정 지역의 최적 방문 시기를 알고 싶음 (예: "제주 언제 가면 좋아?")
- popular: 한국의 유명한 여행지를 추천받고 싶음 (예: "어느 여행지가 유명해?", "여행지 추천해줘")

의도만 답하세요 (recommend, attraction, best_time, popular 중 하나):"""

    response = get_llm().invoke(prompt)
    intent = response.content.strip().lower()
    
    # 목적지 추출
    destination_prompt = f"""다음 텍스트에서 목적지만 추출하세요:

"{user_input}"

목적지만 답하세요 (예: 부산, 제주도, 춘천, 강릉 등).
목적지가 없으면 "없음"이라고 답하세요:"""

    dest_response = get_llm().invoke(destination_prompt)
    destination = dest_response.content.strip()
    
    if destination == "없음":
        destination = None
    
    state["intent"] = intent
    if destination:
        state["destination"] = destination
    
    return state


def recommend_agent(state: RegionState) -> RegionState:
    """Recommend Agent - 지역 추천"""
    from agents.tool.region_tools import recommend_regions_tool
    
    destination = state.get("destination", "부산")
    
    result = recommend_regions_tool.invoke({"destination": destination})
    state["result"] = result
    state["final_response"] = f"{destination} 지역 {result.get('count', 0)}개를 추천했습니다!"
    
    return state


def attraction_agent(state: RegionState) -> RegionState:
    """Attraction Agent - 명소 검색"""
    from agents.tool.region_tools import get_region_attractions_tool
    
    destination = state.get("destination", "부산")
    
    result = get_region_attractions_tool.invoke({"region": destination})
    state["result"] = result
    state["final_response"] = f"{destination} 명소 정보를 찾았습니다!"
    
    return state


def best_time_agent(state: RegionState) -> RegionState:
    """Best Time Agent - 최적 방문 시기"""
    from agents.tool.region_tools import get_region_best_time_tool
    
    destination = state.get("destination", "부산")
    
    result = get_region_best_time_tool.invoke({"region": destination})
    state["result"] = result
    state["final_response"] = f"{destination} 최적 방문 시기를 분석했습니다!"
    
    return state


def popular_agent(state: RegionState) -> RegionState:
    """Popular Agent - 인기 여행지 추천"""
    from agents.tool.region_tools import get_popular_destinations_tool
    
    travel_style = state.get("travel_style")
    
    result = get_popular_destinations_tool.invoke({"travel_style": travel_style, "top_n": 5})
    state["result"] = result
    state["final_response"] = "한국 인기 여행지를 추천했습니다! 🌟"
    
    return state


def route_to_agent(state: RegionState) -> Literal["recommend", "attraction", "best_time", "popular"]:
    """의도에 따라 에이전트 라우팅"""
    intent = state.get("intent", "recommend")
    
    if intent == "attraction":
        return "attraction"
    elif intent == "best_time":
        return "best_time"
    elif intent == "popular":
        return "popular"
    else:
        return "recommend"


# LangGraph 생성
workflow = StateGraph(RegionState)

# 노드 추가
workflow.add_node("classify", classify_intent)
workflow.add_node("recommend", recommend_agent)
workflow.add_node("attraction", attraction_agent)
workflow.add_node("best_time", best_time_agent)
workflow.add_node("popular", popular_agent)

# 엣지 추가
workflow.set_entry_point("classify")
workflow.add_conditional_edges(
    "classify",
    route_to_agent,
    {
        "recommend": "recommend",
        "attraction": "attraction",
        "best_time": "best_time",
        "popular": "popular"
    }
)
workflow.add_edge("recommend", END)
workflow.add_edge("attraction", END)
workflow.add_edge("best_time", END)
workflow.add_edge("popular", END)

# 컴파일
region_graph = workflow.compile()


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🗺️ Region LangGraph 테스트")
    print("=" * 60)
    
    # 테스트 1: 지역 추천
    print("\n테스트 1: 지역 추천")
    result = region_graph.invoke({
        "user_input": "춘천갈래"
    })
    print(f"결과: {result['final_response']}")
    print(f"목적지: {result.get('destination', '없음')}")
    
    print("\n완료!")
