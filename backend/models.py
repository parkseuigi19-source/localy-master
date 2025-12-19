from sqlalchemy import Column, Integer, String, Date, DateTime, func, ForeignKey, Text 
from core.database import Base
from datetime import datetime

class WithdrawnUser(Base):
    __tablename__ = "withdrawn_users"

    # 탈퇴한 아이디만 저장 (Primary Key로 설정하여 중복 방지)
    user_id = Column(String(50), primary_key=True) 
    deleted_at = Column(DateTime, default=datetime.now) # 언제 탈퇴했는지
    
# 유저 정보 모델
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


# 페르소나 보드 모델
class Persona(Base):
    __tablename__ = "persona"

    # 기본키, 자동 증가
    persona_seq_no = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="페르소나 index 번호")
    
    # 외래키 - 유저
    user_seq_no = Column(Integer, ForeignKey('user.user_seq_no'), nullable=False, comment="유저 index 번호")
    
    # 페르소나 정보
    persona_id = Column(String(100), nullable=False, comment="페르소나 id")
    persona_like_food = Column(String(150), nullable=False, comment="선호 음식")
    persona_hate_food = Column(String(150), nullable=False, comment="비선호 음식")
    persona_theme = Column(String(150), nullable=True, comment="선호 테마")
    persona_like_region = Column(String(150), nullable=False, comment="선호 지역")
    persona_avoid_region = Column(String(150), nullable=False, comment="비선호 지역")
    persona_transportation = Column(String(150), nullable=False, comment="이동 수단")
    persona_travel_budget = Column(Integer, nullable=False, comment="여행 예산")
    
    # 주의: 원본 DB 컬럼명에 공백이 있어서 백틱 사용
    persona_accommodation_type = Column('persona_accommodation type', String(150), nullable=False, comment="숙소 종류")


# 게시판 모델
class Board(Base):
    __tablename__ = "board"

    # 기본키, 자동 증가
    board_seq_no = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="게시판 index 번호")
    
    # 외래키 - 유저
    user_seq_no = Column(Integer, ForeignKey('user.user_seq_no'), nullable=False, comment="작성자 index 번호")
    
    # 게시판 정보
    board_title = Column(String(200), nullable=False, comment="게시글 제목")
    board_content = Column(Text, nullable=False, comment="게시글 내용")
    board_views = Column(Integer, default=0, nullable=False, comment="조회수")
    board_category = Column(String(50), nullable=True, comment="게시글 카테고리")
    
    # 관리 정보
    board_create_date = Column(DateTime, default=func.now(), nullable=False, comment="게시글 작성일")
    board_update_date = Column(DateTime, default=func.now(), onupdate=func.now(), comment="게시글 수정일")
    board_delete_date = Column(DateTime, nullable=True, comment="게시글 삭제일")
    board_delete_check = Column(String(1), default="N", nullable=False, comment="삭제 여부")


# 파일 모델
class File(Base):
    __tablename__ = "file"

    # 기본키, 자동 증가
    file_seq_no = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="파일 index 번호")
    
    # 외래키 - 유저, 게시판
    user_seq_no = Column(Integer, ForeignKey('user.user_seq_no'), nullable=True, comment="유저 index 번호")
    board_seq_no = Column(Integer, ForeignKey('board.board_seq_no'), nullable=True, comment="게시판 index 번호")
    
    # 파일 정보
    file_name = Column(Text, nullable=False, comment="파일 이름")
    file_rename = Column(Text, nullable=False, comment="변경된 파일 이름")
    file_extension = Column(String(5), nullable=True, comment="파일 확장자")
    
    # 관리 정보
    file_create_date = Column(DateTime, default=func.now(), nullable=False, comment="파일 생성일")