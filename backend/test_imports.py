"""Import 테스트 스크립트"""
import sys
import traceback

print("=" * 60)
print("Import 테스트 시작")
print("=" * 60)

# 1. agents.state import 테스트
try:
    from agents.state import TravelAgentState
    print("✅ agents.state import 성공")
except Exception as e:
    print(f"❌ agents.state import 실패: {e}")
    traceback.print_exc()

# 2. agents.graph import 테스트
try:
    from agents.graph import travel_agent_graph
    print("✅ agents.graph import 성공")
except Exception as e:
    print(f"❌ agents.graph import 실패: {e}")
    traceback.print_exc()

# 3. routers.langgraph_chat import 테스트
try:
    from routers import langgraph_chat
    print("✅ routers.langgraph_chat import 성공")
except Exception as e:
    print(f"❌ routers.langgraph_chat import 실패: {e}")
    traceback.print_exc()

# 4. main import 테스트
try:
    import main
    print("✅ main import 성공")
except Exception as e:
    print(f"❌ main import 실패: {e}")
    traceback.print_exc()

print("=" * 60)
print("테스트 완료")
print("=" * 60)
