from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db  # DB 세션 의존성 (구현 필요)
from models import User
from schemas.user import UserCreate, UserLogin, UserResponse
from core.security import get_password_hash, verify_password
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
from datetime import datetime, timedelta
from jose import JWTError, jwt
from models import User, WithdrawnUser


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


# 토큰 설정 (실제 배포할 땐 아주 복잡한 비밀번호로 환경변수에 숨겨야 함)
SECRET_KEY = "localy_secret_key_very_secure" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24시간 유지

# 토큰 생성 함수
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 이메일 인증번호 임시 저장소 (실제로는 Redis 또는 DB 사용 권장)
verification_codes = {}

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationCheck(BaseModel):
    email: EmailStr
    code: str


# 이메일 인증번호 발송 API
@router.post("/send-verification")
async def send_verification_code(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    이메일로 6자리 인증번호를 발송합니다.
    Gmail SMTP를 사용합니다.
    """
    # 이메일 중복 체크
    existing_user = db.query(User).filter(User.user_email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 이메일입니다.")
    
    # 6자리 랜덤 인증번호 생성
    verification_code = ''.join(random.choices(string.digits, k=6))
    
    # 인증번호 저장 (5분 유효)
    expiry_time = datetime.now() + timedelta(minutes=5)
    verification_codes[request.email] = {
        'code': verification_code,
        'expiry': expiry_time
    }
    
    # Gmail SMTP 설정 (환경변수로 관리 권장)
    # TODO: 실제 Gmail 계정 정보로 교체하세요
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "kongdu300@gmail.com"  # 발신자 이메일
    sender_password = "axaq viqu objl kpxl"   # Gmail 앱 비밀번호
    
    try:
        # 이메일 메시지 생성
        message = MIMEMultipart("alternative")
        message["Subject"] = "야옹이 여행 - 이메일 인증번호"
        message["From"] = sender_email
        message["To"] = request.email
        
        # HTML 이메일 본문
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px;">
              <h2 style="color: #2D8B5F;">🐱 야옹이 여행 이메일 인증</h2>
              <p>회원가입을 위한 인증번호입니다.</p>
              <div style="background-color: white; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <h1 style="color: #2D8B5F; letter-spacing: 5px;">{verification_code}</h1>
              </div>
              <p style="color: #666; font-size: 14px;">이 인증번호는 5분간 유효합니다.</p>
              <p style="color: #999; font-size: 12px;">본인이 요청하지 않았다면 이 이메일을 무시하세요.</p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        message.attach(part)
        
        # SMTP 서버 연결 및 이메일 발송
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, request.email, message.as_string())
        
        return {"message": "인증번호가 이메일로 전송되었습니다."}
    
    except Exception as e:
        # 실제 이메일 발송 실패시 콘솔에 인증번호 출력 (개발용)
        print(f"[개발용] 이메일 발송 실패. 인증번호: {verification_code}")
        print(f"에러: {str(e)}")
        # 개발 환경에서는 인증번호를 반환 (프로덕션에서는 제거)
        return {"message": "인증번호가 이메일로 전송되었습니다.", "dev_code": verification_code}

# 이메일 인증번호 확인 API
@router.post("/verify-email")
async def verify_email_code(request: EmailVerificationCheck):
    """
    이메일 인증번호를 확인합니다.
    """
    # 저장된 인증번호 확인
    if request.email not in verification_codes:
        raise HTTPException(status_code=400, detail="인증번호가 발송되지 않았습니다.")
    
    stored_data = verification_codes[request.email]
    
    # 유효기간 확인
    if datetime.now() > stored_data['expiry']:
        del verification_codes[request.email]
        raise HTTPException(status_code=400, detail="인증번호가 만료되었습니다.")
    
    # 인증번호 확인
    if stored_data['code'] != request.code:
        raise HTTPException(status_code=400, detail="인증번호가 올바르지 않습니다.")
    
    # 인증 성공 - 저장소에서 삭제
    del verification_codes[request.email]
    
    return {"message": "이메일 인증이 완료되었습니다."}

# 0. 아이디 중복 확인 API
@router.get("/check-username/{user_id}")
async def check_username(user_id: str, db: Session = Depends(get_db)):
    # 1. User 테이블 확인 (현재 회원 + 소프트 삭제된 회원)
    db_user = db.query(User).filter(User.user_id == user_id).first()
    
    if db_user:
        # 1-1. 소프트 삭제된 회원인지 체크 ('Y'면 차단)
        if db_user.user_delete_check == 'Y':
            return {"available": False, "message": "탈퇴한 회원의 아이디는 다시 사용할 수 없습니다."}
        else:
            return {"available": False, "message": "이미 사용 중인 아이디입니다."}
    
    # 2. [추가] WithdrawnUser 테이블 확인 (혹시 예전 방식으르 삭제된 기록이 있다면 차단)
    # models.py에 WithdrawnUser가 정의되어 있어야 합니다.
    try:
        withdrawn_user = db.query(WithdrawnUser).filter(WithdrawnUser.user_id == user_id).first()
        if withdrawn_user:
             return {"available": False, "message": "탈퇴한 회원의 아이디는 다시 사용할 수 없습니다."}
    except:
        pass # 테이블이 없거나 에러나면 패스 (소프트 삭제가 메인이므로)

    # 3. 아무곳에도 없으면 사용 가능
    return {"available": True, "message": "사용 가능한 아이디입니다."}
# 닉네임 중복 확인 API
@router.get("/check-nickname/{nickname}")
async def check_nickname(nickname: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.user_nickname == nickname).first()
    if db_user:
        return {"available": False, "message": "이미 사용 중인 닉네임입니다."}
    return {"available": True, "message": "사용 가능한 닉네임입니다."}

# 1. 회원가입 API
# ---------------------------------------------------
# [핵심 수정] 회원가입 (탈퇴 아이디 차단)
# ---------------------------------------------------
@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    # 1. ID 중복 및 탈퇴 여부 체크
    db_user = db.query(User).filter(User.user_id == user.user_id).first()
    if db_user:
        if db_user.user_delete_check == 'Y':
            raise HTTPException(status_code=400, detail="탈퇴한 아이디로는 재가입할 수 없습니다.")
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    
    # 이메일 중복 체크 등 나머지 로직
    hashed_password = get_password_hash(user.user_pw)
    
    print(f"\n=== 회원가입 ===")
    print(f"아이디: {user.user_id}")
    print(f"평문 비밀번호: {user.user_pw}")
    print(f"해시된 비밀번호: {hashed_password[:60]}...")
    
    new_user = User(
        user_id=user.user_id,
        user_pw=hashed_password,  # 암호화해서 저장
        user_name=user.user_name,
        user_nickname=user.user_nickname,
        user_email=user.user_email,
        user_post=user.user_post,
        user_addr1=user.user_addr1,
        user_addr2=user.user_addr2,
        user_birth=user.user_birth,
        user_gender=user.user_gender,
        # 기본값 설정
        user_delete_check='N',
        user_delete_date=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. 로그인 API (디버그 로깅 추가 + DB 없이도 작동)
@router.post("/login")
async def login(user_req: UserLogin, db: Session = Depends(get_db)):
    print(f"\n=== 로그인 시도 ===")
    print(f"입력된 아이디: {user_req.user_id}")
    print(f"입력된 비밀번호: {user_req.user_pw}")
    
    # DB가 None이면 바로 더미 사용자로 로그인
    if db is None:
        print(f"⚠️ DB 없음: 더미 사용자로 로그인 허용 (개발 모드)")
        access_token = create_access_token(data={"sub": user_req.user_id})
        return {
            "message": "로그인 성공! (개발 모드 - DB 없음)",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_req.user_id,
            "user_name": "테스트 사용자",
            "user_nickname": "냥이",
            "user_email": "test@example.com",
            "user_phone": "",
            "user_post": "",
            "user_addr1": "",
            "user_addr2": "",
            "user_birth": "",
            "user_gender": "",
            "non_preferred_food": "",
            "non_preferred_region": ""
        }
    
    try:
        # 1. ID로 유저 찾기
        user = db.query(User).filter(User.user_id == user_req.user_id).first()
        
        if not user:
            print(f"❌ 해당 아이디로 등록된 사용자를 찾을 수 없습니다: {user_req.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
            )
        
        print(f"✅ 사용자 찾음: {user.user_id}")
        print(f"저장된 해시: {user.user_pw[:60]}...")
        
        # 2. 비밀번호 검증
        password_valid = verify_password(user_req.user_pw, user.user_pw)
        print(f"비밀번호 검증 결과: {password_valid}")
        
        if not password_valid:
            print(f"❌ 비밀번호 불일치!")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
            )
        
        print(f"✅ 로그인 성공!")
        
        # 3. 토큰 발급
        access_token = create_access_token(data={"sub": user.user_id})
        return {
            "message": "로그인 성공!",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_nickname": user.user_nickname,
            "user_email": user.user_email,
            "user_phone": user.user_phone if hasattr(user, "user_phone") else "",
            "user_post": user.user_post,
            "user_addr1": user.user_addr1,
            "user_addr2": user.user_addr2,
            "user_birth": str(user.user_birth) if user.user_birth else "",
            "user_gender": user.user_gender,
            "non_preferred_food": user.non_preferred_food if hasattr(user, "non_preferred_food") else "",
            "non_preferred_region": user.non_preferred_region if hasattr(user, "non_preferred_region") else ""
        }
    
    except Exception as e:
        # DB 연결 실패 시 더미 사용자로 로그인 허용 (개발 환경용)
        print(f"⚠️ DB 연결 실패: {e}")
        print(f"🔧 더미 사용자로 로그인 허용 (개발 모드)")
        
        # 더미 토큰 발급
        access_token = create_access_token(data={"sub": user_req.user_id})
        return {
            "message": "로그인 성공! (개발 모드 - DB 없음)",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_req.user_id,
            "user_name": "테스트 사용자",
            "user_nickname": "냥이",
            "user_email": "test@example.com",
            "user_phone": "",
            "user_post": "",
            "user_addr1": "",
            "user_addr2": "",
            "user_birth": "",
            "user_gender": "",
            "non_preferred_food": "",
            "non_preferred_region": ""
        }


# -----------------------------------------------------------
# [추가] 비밀번호 변경 기능
# -----------------------------------------------------------

class PasswordChangeRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str

@router.put("/change-password")
async def change_password(request: PasswordChangeRequest, db: Session = Depends(get_db)):
    """
    로그인한 사용자의 비밀번호를 변경합니다.
    """
    user = db.query(User).filter(User.user_id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not verify_password(request.current_password, user.user_pw):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")

    user.user_pw = get_password_hash(request.new_password)
    
    db.add(user)
    db.commit()
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


# ---------------------------------------------------
# [핵심 수정] 회원 탈퇴 (소프트 삭제 적용)
# ---------------------------------------------------
@router.delete("/withdraw/{user_id}")
async def withdraw_user(user_id: str, db: Session = Depends(get_db)):
    """
    회원 탈퇴: DB에서 사용자 정보를 영구 삭제합니다.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # [NEW] DB팀 요청사항: DELETE 대신 UPDATE
    user.user_delete_check = 'Y'
    user.user_delete_date = datetime.now()
    
    db.commit() # 데이터는 남기고 상태만 변경
    
    return {"message": "회원 탈퇴가 완료되었습니다."}
#
# -----------------------------------------------------------
# [추가] 개인정보 및 페르소나 수정 기능
# -----------------------------------------------------------

class UserUpdateRequest(BaseModel):
    user_id: str
    user_nickname: str | None = None
    user_phone: str | None = None
    user_post: str | None = None
    user_addr1: str | None = None
    user_addr2: str | None = None
    non_preferred_food: str | None = None   
    non_preferred_region: str | None = None

@router.put("/update-profile")
async def update_profile(request: UserUpdateRequest, db: Session = Depends(get_db)):
    """
    사용자 정보(개인정보 + 페르소나)를 수정합니다.
    """
    user = db.query(User).filter(User.user_id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    if request.user_nickname is not None:
        user.user_nickname = request.user_nickname
    if request.user_phone is not None:
        user.user_phone = request.user_phone
    if request.user_post is not None:
        user.user_post = request.user_post
    if request.user_addr1 is not None:
        user.user_addr1 = request.user_addr1
    if request.user_addr2 is not None:
        user.user_addr2 = request.user_addr2
        
    if request.non_preferred_food is not None:
        user.non_preferred_food = request.non_preferred_food
    if request.non_preferred_region is not None:
        user.non_preferred_region = request.non_preferred_region
        
    db.commit()
    db.refresh(user)
    
    return {"message": "정보가 성공적으로 수정되었습니다."}