from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. DB 연결 주소 (URL)
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://유저명:비밀번호@localhost:3306/db이름"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://travel:travel12!!@192.168.0.222:3306/travel_platform"

# 2. 엔진 생성 (DB와 연결되는 핵심 객체)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. 세션 생성 (실제 데이터 작업을 수행하는 도구)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 모델들이 상속받을 기본 클래스 (이걸로 테이블을 만듭니다)
Base = declarative_base()

# 5. DB 세션을 가져오는 함수 (라우터에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()