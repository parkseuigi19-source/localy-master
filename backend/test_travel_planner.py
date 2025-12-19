"""통합 테스트 스크립트"""
import sys
import os

# 환경 변수 먼저 로드
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
print(f"환경 변수 로드: {env_path}")
print(f"OPENAI_API_KEY 설정됨: {bool(os.getenv('OPENAI_API_KEY'))}")

# 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("🐱 Travel Planner 통합 테스트")
print("=" * 60)

# 1. Import 테스트
print("\n[1] Import 테스트...")
try:
    from agents.state import TravelPlannerState
    print("✅ TravelPlannerState import 성공")
except Exception as e:
    print(f"❌ TravelPlannerState import 실패: {e}")
    sys.exit(1)

try:
    from agents.graph import travel_planner_graph
    print("✅ travel_planner_graph import 성공")
except Exception as e:
    print(f"❌ travel_planner_graph import 실패: {e}")
    sys.exit(1)

# 2. 초기 상태 테스트
print("\n[2] 초기 상태 생성 테스트...")
try:
    initial_state = {
        "messages": [],
        "user_input": "여행 가고 싶어",
        "current_phase": "required_info",
        "required_info": {},
        "required_info_complete": False,
        "preferences": {},
        "selected_items": {},
        "agent_results": {},
        "itinerary": None,
        "next_agent": None,
        "final_response": ""
    }
    print("✅ 초기 상태 생성 성공")
except Exception as e:
    print(f"❌ 초기 상태 생성 실패: {e}")
    sys.exit(1)

# 3. Graph 실행 테스트
print("\n[3] Graph 실행 테스트...")
print("사용자 입력: '여행 가고 싶어'")
try:
    result = travel_planner_graph.invoke(initial_state)
    print(f"✅ Graph 실행 성공")
    print(f"\n응답: {result['final_response']}")
    print(f"Phase: {result.get('current_phase', 'unknown')}")
    print(f"필수 정보 완료: {result.get('required_info_complete', False)}")
except Exception as e:
    print(f"❌ Graph 실행 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Phase 2 테스트 (맛집 검색)
print("\n[4] Phase 2 테스트 (맛집 검색)...")
print("사용자 입력: '강남 맛집 추천해줘'")
try:
    phase2_state = {
        "messages": [],
        "user_input": "강남 맛집 추천해줘",
        "current_phase": "preference_gathering",
        "required_info": {
            "destination": "서울",
            "departure": "인천",
            "departure_time": "오전 9시",
            "dates": "이번 주말",
            "budget": "50만원"
        },
        "required_info_complete": True,
        "preferences": {},
        "selected_items": {},
        "agent_results": {},
        "itinerary": None,
        "next_agent": None,
        "final_response": ""
    }
    
    result2 = travel_planner_graph.invoke(phase2_state)
    print(f"✅ Phase 2 실행 성공")
    print(f"\n응답: {result2['final_response'][:200]}...")
except Exception as e:
    print(f"❌ Phase 2 실행 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 모든 테스트 완료!")
print("=" * 60)
