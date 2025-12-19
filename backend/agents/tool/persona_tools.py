"""페르소나 관리 툴 - CRUD 4개 툴 (DB 연동)

Tools:
1. create_persona: 페르소나 생성
2. get_persona: 페르소나 조회
3. update_persona: 페르소나 수정
4. delete_persona: 페르소나 삭제

DB: MySQL 연동 (SQLAlchemy)
"""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from langchain.tools import tool

from core.database import SessionLocal
from models import Persona, User
from schemas.data_models import UserPersona, AgentResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS - DB <-> Schema 변환
# ============================================================================

def _db_to_persona(db_persona: Persona, user_id: str) -> UserPersona:
    """DB Persona 모델 → UserPersona 스키마 변환"""
    
    # 음식 선호도 파싱
    food_prefs = []
    if db_persona.persona_like_food:
        food_prefs = [f.strip() for f in db_persona.persona_like_food.split(',')]
    
    # 관심사 파싱 (테마)
    interests = []
    if db_persona.persona_theme:
        interests = [i.strip() for i in db_persona.persona_theme.split(',')]
    
    # 여행 스타일 파싱 (선호 지역)
    travel_style = []
    if db_persona.persona_like_region:
        travel_style = [r.strip() for r in db_persona.persona_like_region.split(',')]
    
    # 예산 레벨 변환
    budget = db_persona.persona_travel_budget
    if budget < 500000:
        budget_level = "저"
    elif budget < 1000000:
        budget_level = "중"
    else:
        budget_level = "고"
    
    return UserPersona(
        user_id=user_id,
        age_group="30대",  # DB에 없으면 기본값
        gender=None,
        travel_style=travel_style[:3] if travel_style else ["힐링"],
        budget_level=budget_level,
        food_preferences=food_prefs,
        accommodation_style=db_persona.persona_accommodation_type,
        interests=interests,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )


def _persona_to_db(persona: UserPersona, user_seq_no: int) -> dict:
    """UserPersona 스키마 → DB Persona 모델 데이터 변환"""
    return {
        'user_seq_no': user_seq_no,
        'persona_id': persona.user_id,
        'persona_like_food': ','.join(persona.food_preferences),
        'persona_hate_food': '',  # 기본값
        'persona_theme': ','.join(persona.interests),
        'persona_like_region': ','.join(persona.travel_style),
        'persona_avoid_region': '',  # 기본값
        'persona_transportation': '대중교통',  # 기본값
        'persona_travel_budget': {
            '저': 300000,
            '중': 700000,
            '고': 1500000
        }.get(persona.budget_level, 700000),
        'persona_accommodation_type': persona.accommodation_style
    }


# ============================================================================
# TOOL 1: 페르소나 생성
# ============================================================================

@tool
def create_persona(user_id: str, persona_data: UserPersona) -> dict:
    """
    새 페르소나 생성
    
    Args:
        user_id: 사용자 ID (예: "user123")
        persona_data: UserPersona 스키마 데이터
    
    Returns:
        AgentResponse: 표준 응답 형식
    """
    db = SessionLocal()
    try:
        logger.info(f"🎯 페르소나 생성: {user_id}")
        
        # 1. 사용자 존재 확인
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"사용자 '{user_id}'를 찾을 수 없습니다",
                error="User not found"
            ).model_dump()
        
        # 2. 기존 페르소나 확인
        existing = db.query(Persona).filter(
            Persona.user_seq_no == user.user_seq_no
        ).first()
        
        if existing:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"'{user_id}' 페르소나가 이미 존재합니다. update_persona를 사용하세요",
                error="Persona already exists"
            ).model_dump()
        
        # 3. 새 페르소나 생성
        db_data = _persona_to_db(persona_data, user.user_seq_no)
        new_persona = Persona(**db_data)
        
        db.add(new_persona)
        db.commit()
        db.refresh(new_persona)
        
        # 4. 응답 생성
        result_persona = _db_to_persona(new_persona, user_id)
        
        logger.info(f"✅ 페르소나 생성 완료: {user_id}")
        return AgentResponse(
            success=True,
            agent_name="persona",
            data=[result_persona.model_dump()],
            count=1,
            message=f"'{user_id}' 페르소나 생성 완료! 🎉"
        ).model_dump()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 페르소나 생성 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="persona",
            message="페르소나 생성 중 오류 발생",
            error=str(e)
        ).model_dump()
    finally:
        db.close()


# ============================================================================
# TOOL 2: 페르소나 조회
# ============================================================================

@tool
def get_persona(user_id: str) -> dict:
    """
    사용자 페르소나 조회
    
    Args:
        user_id: 사용자 ID
    
    Returns:
        AgentResponse: 표준 응답 형식
    """
    db = SessionLocal()
    try:
        logger.info(f"🔍 페르소나 조회: {user_id}")
        
        # 1. 사용자 찾기
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"사용자 '{user_id}'를 찾을 수 없습니다",
                error="User not found"
            ).model_dump()
        
        # 2. 페르소나 찾기
        db_persona = db.query(Persona).filter(
            Persona.user_seq_no == user.user_seq_no
        ).first()
        
        if not db_persona:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"'{user_id}' 페르소나가 없습니다",
                error="Persona not found"
            ).model_dump()
        
        # 3. 변환
        persona = _db_to_persona(db_persona, user_id)
        
        logger.info(f"✅ 페르소나 조회 완료: {user_id}")
        return AgentResponse(
            success=True,
            agent_name="persona",
            data=[persona.model_dump()],
            count=1,
            message=f"'{user_id}' 페르소나 조회 완료! 📋"
        ).model_dump()
        
    except Exception as e:
        logger.error(f"❌ 페르소나 조회 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="persona",
            message="페르소나 조회 중 오류 발생",
            error=str(e)
        ).model_dump()
    finally:
        db.close()


# ============================================================================
# TOOL 3: 페르소나 수정
# ============================================================================

@tool
def update_persona(user_id: str, persona_data: UserPersona) -> dict:
    """
    페르소나 수정
    
    Args:
        user_id: 사용자 ID
        persona_data: 수정할 UserPersona 데이터
    
    Returns:
        AgentResponse: 표준 응답 형식
    """
    db = SessionLocal()
    try:
        logger.info(f"✏️ 페르소나 수정: {user_id}")
        
        # 1. 사용자 찾기
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"사용자 '{user_id}'를 찾을 수 없습니다",
                error="User not found"
            ).model_dump()
        
        # 2. 페르소나 찾기
        db_persona = db.query(Persona).filter(
            Persona.user_seq_no == user.user_seq_no
        ).first()
        
        if not db_persona:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"'{user_id}' 페르소나가 없습니다. create_persona를 사용하세요",
                error="Persona not found"
            ).model_dump()
        
        # 3. 업데이트
        update_data = _persona_to_db(persona_data, user.user_seq_no)
        for key, value in update_data.items():
            if key != 'user_seq_no':  # user_seq_no는 변경 안 함
                setattr(db_persona, key, value)
        
        db.commit()
        db.refresh(db_persona)
        
        # 4. 응답 생성
        result_persona = _db_to_persona(db_persona, user_id)
        
        logger.info(f"✅ 페르소나 수정 완료: {user_id}")
        return AgentResponse(
            success=True,
            agent_name="persona",
            data=[result_persona.model_dump()],
            count=1,
            message=f"'{user_id}' 페르소나 수정 완료! ✏️"
        ).model_dump()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 페르소나 수정 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="persona",
            message="페르소나 수정 중 오류 발생",
            error=str(e)
        ).model_dump()
    finally:
        db.close()


# ============================================================================
# TOOL 4: 페르소나 삭제
# ============================================================================

@tool
def delete_persona(user_id: str) -> dict:
    """
    페르소나 삭제
    
    Args:
        user_id: 사용자 ID
    
    Returns:
        AgentResponse: 표준 응답 형식
    """
    db = SessionLocal()
    try:
        logger.info(f"🗑️ 페르소나 삭제: {user_id}")
        
        # 1. 사용자 찾기
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"사용자 '{user_id}'를 찾을 수 없습니다",
                error="User not found"
            ).model_dump()
        
        # 2. 페르소나 찾기
        db_persona = db.query(Persona).filter(
            Persona.user_seq_no == user.user_seq_no
        ).first()
        
        if not db_persona:
            return AgentResponse(
                success=False,
                agent_name="persona",
                message=f"'{user_id}' 페르소나가 없습니다",
                error="Persona not found"
            ).model_dump()
        
        # 3. 삭제
        db.delete(db_persona)
        db.commit()
        
        logger.info(f"✅ 페르소나 삭제 완료: {user_id}")
        return AgentResponse(
            success=True,
            agent_name="persona",
            data=[],
            count=0,
            message=f"'{user_id}' 페르소나 삭제 완료! 🗑️"
        ).model_dump()
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 페르소나 삭제 실패: {e}")
        return AgentResponse(
            success=False,
            agent_name="persona",
            message="페르소나 삭제 중 오류 발생",
            error=str(e)
        ).model_dump()
    finally:
        db.close()


# ============================================================================
# TOOL LIST (에이전트에서 import용)
# ============================================================================

persona_tools = [
    create_persona,
    get_persona,
    update_persona,
    delete_persona
]
