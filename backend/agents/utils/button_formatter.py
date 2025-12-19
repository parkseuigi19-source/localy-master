"""
UI 버튼 생성 유틸리티
채팅 메시지 안에 표시될 버튼 UI 메타데이터 생성
"""

from typing import Dict, Any


def create_button_ui(
    text: str,
    action: str,
    style: str = "primary"
) -> Dict[str, Any]:
    """
    버튼 UI 요소 생성
    
    Args:
        text: 버튼 텍스트
        action: 버튼 액션 ("open_calendar", "select_place" 등)
        style: 버튼 스타일 ("primary", "secondary", "outline")
    
    Returns:
        UI 요소 딕셔너리
    """
    return {
        "type": "button",
        "data": {
            "text": text,
            "action": action,
            "style": style
        }
    }
