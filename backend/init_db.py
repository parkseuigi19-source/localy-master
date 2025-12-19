"""
DB 초기화 및 테스트 계정 생성 스크립트
- MySQL에 테이블 자동 생성
- 테스트용 계정 3개 자동 삽입
"""
import bcrypt
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Date, DateTime, func, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base

########################## DB 정보 세팅 ##########################
# 1. DB 연결 주소 (URL) 세팅
SERVER_URL = "mysql+pymysql://root:1234@localhost:3306"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/travel_platform"

# 2. 일단 DB 접속 > 접속이 안되면은 데이터베이스 생성
server_engine = create_engine(SERVER_URL, isolation_level = "AUTOCOMMIT")

# 3. 데이터베이스 접속 시도 > 안되면 생성 시도
try:
    with server_engine.connect() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS travel_platform DEFAULT CHARACTER SET utf8mb4;")
        )
        print("travel_platform 확인 또는 생성을 완료 했습니다.")
except SQLAlchemyError as e:
    print(f"travel_platform 확인 또는 생성을 실패 했습니다.\n{e}")

# 4. 엔진 생성 (DB와 연결되는 핵심 객체)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 5. 세션 생성 (실제 데이터 작업을 수행하는 도구)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 6. 모델들이 상속받을 기본 클래스 (이걸로 테이블을 만듭니다)
Base = declarative_base()

########################## 유저 정보 모델 세팅 ##########################
class User(Base):
    __tablename__ = "user"

    # 기본키, 자동 증가
    user_seq_no = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 유저 아이디 (중복 불가)
    user_id = Column(String(20), unique=True, nullable=False)
    
    # 비밀번호 (암호화되어 저장됨)
    user_pw = Column(String(100), nullable=False)
    
    # 비밀번호 체크 여부 (기본값 Y)
    user_pw_check = Column(String(1), default='Y', nullable=False)
    
    # 유저 이름
    user_name = Column(String(10), nullable=False)
    
    # 유저 닉네임
    user_nickname = Column(String(20), nullable=False)
    
    # 이메일 (중복 불가)
    user_email = Column(String(50), unique=True, nullable=False)
    
    # 주소 정보
    user_post = Column(String(5), nullable=False)
    user_addr1 = Column(String(100), nullable=False)
    user_addr2 = Column(String(100), nullable=True) # 상세주소는 없을 수도 있음 (NULL 허용)
    
    # 생년월일 및 성별
    user_birth = Column(Date, default="2000-01-01", nullable=False)
    user_gender = Column(String(1), nullable=False)
    
    # 관리 정보 (자동 생성)
    user_create_date = Column(DateTime, default=func.now(), nullable=False)
    user_update_date = Column(DateTime, default=func.now(), onupdate=func.now())
    user_delete_date = Column(DateTime, nullable=True)
    user_delete_check = Column(String(1), default="N", nullable=False)

########################## 함수 세팅 ##########################
# 패스워드 해싱 및 검증 함수
def get_password_hash(password: str) -> str:
    """
    비밀번호를 해싱합니다.
    bcrypt는 72바이트 제한이 있으므로 자동으로 잘라냅니다.
    """
    # 비밀번호를 UTF-8로 인코딩하고 72바이트로 제한
    password_bytes = password.encode('utf-8')[:72]
    
    # salt를 생성하고 비밀번호를 해싱
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 문자열로 반환
    return hashed.decode('utf-8')

def init_database():
    """데이터베이스 테이블 생성"""
    print("=" * 60)
    print("🔧 데이터베이스 테이블 생성 중...")
    print("=" * 60)
    
    # 모든 테이블 생성 (없으면 만들고, 있으면 넘어감)
    Base.metadata.create_all(bind=engine)
    
    print("✅ 테이블 생성 완료!")
    print(f"   - user 테이블")
    print(f"   - personas 테이블")
    print(f"   - file 테이블")
    print(f"   - board 테이블")
    print()

def create_test_users(db: Session):
    """테스트용 계정 3개 생성"""
    print("=" * 60)
    print("👤 테스트 계정 생성 중...")
    print("=" * 60)
    
    # 기존 테스트 계정이 있는지 확인
    existing_user = db.query(User).filter(User.user_id == "test1").first()
    if existing_user:
        print("⚠️  테스트 계정이 이미 존재합니다. 건너뜁니다.")
        return
    
    # 테스트 계정 데이터
    test_users = [
        {
            "user_id": "test1",
            "user_pw": get_password_hash("test1234!"),
            "user_name": "김테스트",
            "user_nickname": "테스터1",
            "user_email": "test1@example.com",
            "user_post": "06234",
            "user_addr1": "서울특별시 강남구 테헤란로 123",
            "user_addr2": "테스트빌딩 101호",
            "user_birth": date(1990, 1, 15),
            "user_gender": "M",
        },
        {
            "user_id": "test2",
            "user_pw": get_password_hash("test1234!"),
            "user_name": "이테스트",
            "user_nickname": "테스터2",
            "user_email": "test2@example.com",
            "user_post": "13529",
            "user_addr1": "경기도 성남시 분당구 판교역로 235",
            "user_addr2": "판교테크빌 202호",
            "user_birth": date(1995, 5, 20),
            "user_gender": "F",
        },
        {
            "user_id": "admin",
            "user_pw": get_password_hash("admin1234!"),
            "user_name": "관리자",
            "user_nickname": "어드민",
            "user_email": "admin@example.com",
            "user_post": "03925",
            "user_addr1": "서울특별시 중구 세종대로 110",
            "user_addr2": "관리동 301호",
            "user_birth": date(1985, 12, 31),
            "user_gender": "M",
        },
    ]
    
    # DB에 삽입
    for user_data in test_users:
        user = User(**user_data)
        db.add(user)
    
    db.commit()
    
    print("✅ 테스트 계정 3개 생성 완료!")
    print()
    print("📋 생성된 계정 목록:")
    print("-" * 60)
    print(f"{'ID':<15} {'비밀번호':<15} {'이름':<10} {'이메일':<25}")
    print("-" * 60)
    print(f"{'test1':<15} {'test1234!':<15} {'김테스트':<10} {'test1@example.com':<25}")
    print(f"{'test2':<15} {'test1234!':<15} {'이테스트':<10} {'test2@example.com':<25}")
    print(f"{'admin':<15} {'admin1234!':<15} {'관리자':<10} {'admin@example.com':<25}")
    print("-" * 60)
    print()

def main():
    """메인 실행 함수"""
    print()
    print("🚀 AIX Travel Platform - DB 초기화 스크립트")
    print()
    
    # 1. 테이블 생성
    init_database()
    
    # 2. 테스트 계정 생성
    db = SessionLocal()
    try:
        create_test_users(db)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
    
    print("=" * 60)
    print("🎉 DB 초기화 완료!")
    print("=" * 60)
    print()
    print("💡 다음 단계:")
    print("   1. 서버 실행: uvicorn main:app --reload")
    print("   2. API 문서: http://localhost:8000/docs")
    print("   3. 로그인 테스트: test1 / test1234!")
    print()

if __name__ == "__main__":
    main()