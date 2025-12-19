from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 1. DB 연결 주소 (URL) 세팅
# SERVER_URL = "mysql+pymysql://유저명:비밀번호@서버IP:포트" > DB 서버 접속까지의 URL
SERVER_URL = "mysql+pymysql://travel:travel12!!@192.168.0.222:3306"
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://유저명:비밀번호@localhost:3306/db이름" > 테이블 접속까지의 URL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://travel:travel12!!@192.168.0.222:3306/travel_platform"

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

# 7. DB 세션을 가져오는 함수 (라우터에서 사용)
def get_db():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        print(f"⚠️ DB 세션 생성 실패: {e}")
        yield None
    finally:
        if 'db' in locals() and db:
            db.close()