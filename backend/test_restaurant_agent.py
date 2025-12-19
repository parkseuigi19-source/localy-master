"""Restaurant Agent 실제 테스트"""
import sys
import os

# 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

# 환경 변수 로드
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', 'env')
load_dotenv(env_path)

print("=" * 60)
print("🍽️ Restaurant Agent ReAct 테스트")
print("=" * 60)

# Restaurant Agent import
from Langgraph.restaurant_langgraph import restaurant_graph

# 테스트 1: 맛집 검색
print("\n[테스트 1] 맛집 검색")
print("사용자 입력: '강남 맛집 추천해줘'")
try:
    result1 = restaurant_graph.invoke({
        "messages": [("user", "강남 맛집 추천해줘")]
    })
    print(f"\n응답: {result1['messages'][-1].content[:500]}...")
except Exception as e:
    print(f"❌ 에러: {e}")

# 테스트 2: 맛집 유명도 질문
print("\n" + "=" * 60)
print("[테스트 2] 맛집 유명도 질문")
print("사용자 입력: '강남 삼겹살집은 어느정도 유명해?'")
try:
    result2 = restaurant_graph.invoke({
        "messages": [("user", "강남 삼겹살집은 어느정도 유명해?")]
    })
    print(f"\n응답: {result2['messages'][-1].content[:500]}...")
except Exception as e:
    print(f"❌ 에러: {e}")

# 테스트 3: 메뉴 질문
print("\n" + "=" * 60)
print("[테스트 3] 메뉴 질문")
print("사용자 입력: '강남에서 파스타 맛있는 곳 알려줘'")
try:
    result3 = restaurant_graph.invoke({
        "messages": [("user", "강남에서 파스타 맛있는 곳 알려줘")]
    })
    print(f"\n응답: {result3['messages'][-1].content[:500]}...")
except Exception as e:
    print(f"❌ 에러: {e}")

print("\n" + "=" * 60)
print("✅ 테스트 완료!")
print("=" * 60)
