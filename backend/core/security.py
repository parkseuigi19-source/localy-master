import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호를 검증합니다.
    bcrypt는 72바이트 제한이 있으므로 자동으로 잘라냅니다.
    """
    # 비밀번호를 UTF-8로 인코딩하고 72바이트로 제한
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

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