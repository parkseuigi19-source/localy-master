"""
간단한 Coordinator 테스트 스크립트
"""

from agents.coordinator import get_coordinator_response

print("=" * 60)
print("🧪 Coordinator Agent 테스트")
print("=" * 60)

# 테스트 1: 초기 메시지
print("\n[테스트 1] 초기 메시지")
response1 = get_coordinator_response("여행 계획 시작", "test_session_1")
print(f"응답: {response1}\n")

# 테스트 2: 목적지 입력
print("\n[테스트 2] 목적지 입력")
response2 = get_coordinator_response("부산", "test_session_1")
print(f"응답: {response2}\n")

# 테스트 3: 지역 선택
print("\n[테스트 3] 지역 선택")
response3 = get_coordinator_response("해운대", "test_session_1")
print(f"응답: {response3}\n")

# 테스트 4: 날짜 입력 (플로우 진행)
print("\n[테스트 4] 날짜 입력")
response4 = get_coordinator_response("12월 15일부터 17일까지", "test_session_1")
print(f"응답: {response4}\n")

# 테스트 5: 예산 입력
print("\n[테스트 5] 예산 입력")
response5 = get_coordinator_response("50만원", "test_session_1")
print(f"응답: {response5}\n")

# 테스트 6: 인원 입력
print("\n[테스트 6] 인원 입력")
response6 = get_coordinator_response("2명", "test_session_1")
print(f"응답: {response6}\n")

# 테스트 7: 맛집 선호도 - 에이전트 자동 호출 테스트!
print("\n[테스트 7] 맛집 선호도 - 에이전트 자동 호출 테스트!")
print("기대: call_restaurant_agent가 자동으로 호출되어야 함")
response7 = get_coordinator_response("일식", "test_session_1")
print(f"응답: {response7}\n")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
