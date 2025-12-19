"""페르소나 관리 API 라우터

Endpoints:
- POST /persona/create: 페르소나 생성
- GET /persona/{user_id}: 페르소나 조회
- PUT /persona/update: 페르소나 수정
- DELETE /persona/{user_id}: 페르소나 삭제
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from agents import (
    create_persona,
    get_persona,
    update_persona,
    delete_persona
)
from schemas.data_models import UserPersona

router = APIRouter(
    prefix="/persona",
    tags=["persona"],
    responses={404: {"description": "Not found"}},
)

# ============================================================================
# 요청 스키마
# ============================================================================

class PersonaCreateRequest(BaseModel):
    """페르소나 생성 요청"""
    user_id: str
    persona_data: UserPersona

class PersonaUpdateRequest(BaseModel):
    """페르소나 수정 요청"""
    user_id: str
    persona_data: UserPersona

# ============================================================================
# 엔드포인트
# ============================================================================

@router.get("/")
async def read_persona_info():
    """페르소나 API 정보"""
    return {
        "message": "Persona Management API",
        "endpoints": {
            "create": "POST /persona/create",
            "read": "GET /persona/{user_id}",
            "update": "PUT /persona/update",
            "delete": "DELETE /persona/{user_id}"
        }
    }

@router.post("/create")
async def create_persona_endpoint(request: PersonaCreateRequest):
    """
    페르소나 생성
    
    - **user_id**: 사용자 ID (DB에 존재해야 함)
    - **persona_data**: UserPersona 스키마 데이터
    """
    try:
        result = create_persona.func(request.user_id, request.persona_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_persona_endpoint(user_id: str):
    """
    페르소나 조회
    
    - **user_id**: 사용자 ID
    """
    try:
        result = get_persona.func(user_id)
        
        # 페르소나가 없으면 404 반환
        if not result['success']:
            if "찾을 수 없습니다" in result['message']:
                raise HTTPException(status_code=404, detail=result['message'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update")
async def update_persona_endpoint(request: PersonaUpdateRequest):
    """
    페르소나 수정
    
    - **user_id**: 사용자 ID
    - **persona_data**: 수정할 UserPersona 데이터
    """
    try:
        result = update_persona.func(request.user_id, request.persona_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_persona_endpoint(user_id: str):
    """
    페르소나 삭제
    
    - **user_id**: 사용자 ID
    """
    try:
        result = delete_persona.func(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))