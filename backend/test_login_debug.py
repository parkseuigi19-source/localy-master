"""
로그인 문제 진단 스크립트

이 스크립트는 데이터베이스에 저장된 비밀번호 해시와 입력하신 비밀번호를 비교하여
로그인 문제의 원인을 찾습니다.
"""
import sys
sys.path.append('..')

from core.security import verify_password, get_password_hash
from core.database import SessionLocal
from models import User

def diagnose_login_issue(user_id, password):
    """로그인 문제 진단"""
    db = SessionLocal()
    
    try:
        # 1. 사용자 찾기
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다: {user_id}")
            print("   회원가입이 제대로 완료되었는지 확인하세요.")
            return
        
        print(f"\n✅ 사용자 찾음!")
        print(f"   아이디: {user.user_id}")
        print(f"   이름: {user.user_name}")
        print(f"   닉네임: {user.user_nickname}")
        print(f"   이메일: {user.user_email}")
        
        # 2. 저장된 비밀번호 해시 확인
        print(f"\n📝 저장된 비밀번호 해시: {user.user_pw[:60]}...")
        
        # 3. 비밀번호 검증 테스트
        print(f"\n🔐 비밀번호 검증 중...")
        print(f"   입력한 비밀번호: {password}")
        
        is_valid = verify_password(password, user.user_pw)
        
        if is_valid:
            print(f"\n✅ 비밀번호가 일치합니다!")
            print(f"   로그인이 정상적으로 작동해야 합니다.")
        else:
            print(f"\n❌ 비밀번호가 일치하지 않습니다!")
            print(f"\n💡 가능한 원인:")
            print(f"   1. 회원가입 시 다른 비밀번호를 입력했을 수 있습니다.")
            print(f"   2. 대소문자를 확인하세요 (비밀번호는 대소문자를 구분합니다).")
            print(f"   3. 특수문자가 제대로 입력되었는지 확인하세요.")
            
            # 테스트: 새로운 해시 생성 
            print(f"\n🔧 테스트: 입력한 비밀번호로 새 해시 생성...")
            new_hash = get_password_hash(password)
            print(f"   새 해시: {new_hash[:60]}...")
            
            # 새 해시로 검증
            test_verify = verify_password(password, new_hash)
            print(f"   새 해시 검증 결과: {test_verify}")
            
            if test_verify:
                print(f"\n✅ 해싱 시스템은 정상 작동합니다.")
                print(f"\n해결 방법:")
                print(f"   1. 비밀번호 찾기/재설정 기능을 사용하세요.")
                print(f"   2. 또는 회원가입 시 사용한 정확한 비밀번호를 다시 입력하세요.")
            else:
                print(f"\n❌ 해싱 시스템에 문제가 있습니다!")
                print(f"   개발자에게 문의하세요.")
                
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("로그인 문제 진단 스크립트")
    print("="*60)
    
    # 사용자 입력 받기
    user_id = input("\n아이디를 입력하세요: ").strip()
    password = input("비밀번호를 입력하세요: ").strip()
    
    diagnose_login_issue(user_id, password)
    
    print("\n" + "="*60)
