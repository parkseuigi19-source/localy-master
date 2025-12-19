"""페르소나 에이전트 - CRUD 관리

이 에이전트는 tools/persona_tools.py의 4개 툴을 사용합니다:
1. create_persona: 페르소나 생성
2. get_persona: 페르소나 조회
3. update_persona: 페르소나 수정
4. delete_persona: 페르소나 삭제

DB: MySQL 연동 (SQLAlchemy)
"""
import logging
from typing import List
from datetime import datetime
from langchain.tools import BaseTool

# 툴 임포트
from agents.tool.persona_tools import (
    create_persona,
    get_persona,
    update_persona,
    delete_persona,
    persona_tools  # 전체 툴 리스트
)
from schemas.data_models import UserPersona

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonaAgent:
    """페르소나 관리 에이전트 - CRUD"""
    
    def __init__(self):
        self.name = "persona"
        self.tools = persona_tools
        logger.info(f"🎯 페르소나 에이전트 초기화 완료 ({len(self.tools)}개 툴)")
    
    def get_tools(self) -> List[BaseTool]:
        """에이전트의 툴 리스트 반환"""
        return self.tools
    
    def create(self, user_id: str, persona_data: UserPersona):
        """페르소나 생성 (편의 메서드)"""
        return create_persona.func(user_id, persona_data)
    
    def get(self, user_id: str):
        """페르소나 조회 (편의 메서드)"""
        return get_persona.func(user_id)
    
    def update(self, user_id: str, persona_data: UserPersona):
        """페르소나 수정 (편의 메서드)"""
        return update_persona.func(user_id, persona_data)
    
    def delete(self, user_id: str):
        """페르소나 삭제 (편의 메서드)"""
        return delete_persona.func(user_id)


# 전역 에이전트 인스턴스
agent = PersonaAgent()


# ============================================================================
# 완전한 테스트 코드 - 안전하고 상세한 출력!
# ============================================================================
if __name__ == "__main__":
    print("🎯 페르소나 에이전트 테스트\n")
    print(f"✅ 로드된 툴: {len(agent.tools)}개")
    
    for i, tool in enumerate(agent.tools, 1):
        print(f"  {i}. {tool.name}")
    
    # 테스트용 사용자 ID (DB에 있어야 함)
    test_user_id = "test1"
    
    # ========================================================================
    # 테스트 1: 페르소나 생성
    # ========================================================================
    print("\n" + "=" * 50)
    print("테스트 1: 페르소나 생성")
    print("=" * 50)
    print(f"📝 사용자 ID: {test_user_id}")
    print()
    
    test_persona = UserPersona(
        user_id=test_user_id,
        age_group="30대",
        travel_style=["힐링", "맛집투어"],
        budget_level="중",
        food_preferences=["한식", "해산물", "일식"],
        accommodation_style="호텔",
        interests=["사진", "자연", "카페"],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    result = agent.create(test_user_id, test_persona)
    
    print(f"{'✅' if result.get('success') else '❌'} {result.get('message', '응답 없음')}")
    
    if result.get('success'):
        # 안전한 데이터 접근
        if result.get('data') and len(result['data']) > 0:
            persona = result['data'][0]
            print()
            print("📋 생성된 페르소나:")
            print(f"  - 여행 스타일: {persona.get('travel_style', [])}")
            print(f"  - 음식 선호: {persona.get('food_preferences', [])}")
            print(f"  - 예산: {persona.get('budget_level', '정보없음')}")
            print(f"  - 숙소: {persona.get('accommodation_style', '정보없음')}")
            print(f"  - 관심사: {persona.get('interests', [])}")
    else:
        # 에러 메시지 출력
        if result.get('error'):
            print(f"   💬 에러: {result['error']}")
        if "이미 존재" in result.get('message', ''):
            print(f"   💡 Tip: 기존 페르소나가 있습니다. 조회 테스트로 진행합니다.")
    
    # ========================================================================
    # 테스트 2: 페르소나 조회
    # ========================================================================
    print("\n" + "=" * 50)
    print("테스트 2: 페르소나 조회")
    print("=" * 50)
    print(f"📝 사용자 ID: {test_user_id}")
    print()
    
    result2 = agent.get(test_user_id)
    
    print(f"{'✅' if result2.get('success') else '❌'} {result2.get('message', '응답 없음')}")
    
    if result2.get('success'):
        if result2.get('data') and len(result2['data']) > 0:
            persona = result2['data'][0]
            print()
            print("📋 조회된 페르소나:")
            print(f"  - 연령대: {persona.get('age_group', '정보없음')}")
            print(f"  - 여행 스타일: {persona.get('travel_style', [])}")
            print(f"  - 음식 선호: {persona.get('food_preferences', [])}")
            print(f"  - 예산: {persona.get('budget_level', '정보없음')}")
            print(f"  - 숙소 스타일: {persona.get('accommodation_style', '정보없음')}")
            print(f"  - 관심사: {persona.get('interests', [])}")
            
            # 추가 정보
            created = persona.get('created_at', '')
            updated = persona.get('updated_at', '')
            if created:
                print(f"  - 생성일: {created[:19]}")
            if updated:
                print(f"  - 수정일: {updated[:19]}")
    else:
        if result2.get('error'):
            print(f"   💬 에러: {result2['error']}")
    
    # ========================================================================
    # 테스트 3: 페르소나 수정
    # ========================================================================
    print("\n" + "=" * 50)
    print("테스트 3: 페르소나 수정")
    print("=" * 50)
    print(f"📝 변경 사항:")
    print(f"  - 예산: 중 → 고")
    print(f"  - 관심사: 사진, 자연, 카페 → 사진, 쇼핑, 역사")
    print()
    
    # Test 2가 성공했을 때만 진행
    if result2.get('success'):
        test_persona.budget_level = "고"
        test_persona.interests = ["사진", "쇼핑", "역사"]
        
        result3 = agent.update(test_user_id, test_persona)
        
        print(f"{'✅' if result3.get('success') else '❌'} {result3.get('message', '응답 없음')}")
        
        if result3.get('success'):
            if result3.get('data') and len(result3['data']) > 0:
                persona = result3['data'][0]
                print()
                print("📋 수정된 페르소나:")
                print(f"  - 예산: {persona.get('budget_level', '정보없음')}")
                print(f"  - 관심사: {persona.get('interests', [])}")
                
                # 변경 확인
                print()
                print("🔄 변경 확인:")
                print(f"  ✓ 예산 변경됨: 중 → {persona.get('budget_level')}")
                print(f"  ✓ 관심사 변경됨: {len(persona.get('interests', []))}개 항목")
        else:
            if result3.get('error'):
                print(f"   💬 에러: {result3['error']}")
    else:
        print("⚠️  Test 2 실패로 인해 건너뜁니다.")
    
    # ========================================================================
    # 테스트 4: 페르소나 삭제 (선택사항)
    # ========================================================================
    print("\n" + "=" * 50)
    print("테스트 4: 페르소나 삭제 (선택사항)")
    print("=" * 50)
    print("⚠️  실제 DB 데이터가 삭제되므로 주석 처리됨")
    print("💡 삭제를 원하면 아래 주석을 해제하세요:")
    print()
    print("# result4 = agent.delete(test_user_id)")
    print("# print(result4['message'])")
    
    # 실제 삭제는 주석 처리
    # result4 = agent.delete(test_user_id)
    # print(f"{'✅' if result4.get('success') else '❌'} {result4.get('message', '응답 없음')}")
    
    # ========================================================================
    # 결과 요약
    # ========================================================================
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    results = [
        ("생성 (CREATE)", result.get('success', False)),
        ("조회 (READ)", result2.get('success', False)),
        ("수정 (UPDATE)", result3.get('success', False) if 'result3' in locals() else False),
    ]
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}  {name}")
    
    total = sum(1 for _, s in results if s)
    print()
    print(f"🎯 전체: {total}/{len(results)} 성공")
    
    print("\n" + "=" * 50)
    print("🎉 페르소나 에이전트 테스트 완료!")
    print("=" * 50)
    print()
    print("⚠️  주의사항:")
    print("  - 실제 DB에 연결되어 테스트 데이터가 저장됩니다")
    print("  - test1 사용자가 DB에 존재해야 합니다")
    print("  - 삭제 테스트는 기본적으로 비활성화되어 있습니다")
    print()