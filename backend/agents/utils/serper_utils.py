"""
Serper API 통합 유틸리티
웹 검색을 통해 유명한 가게 이름을 먼저 찾고, Google Places로 상세 정보 가져오기
"""

import os
import requests
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def search_with_serper(query: str, num_results: int = 10) -> List[Dict]:
    """
    Serper API로 웹 검색
    
    Args:
        query: 검색 쿼리 (예: "부산 해운대 한옥스테이")
        num_results: 결과 개수
    
    Returns:
        List[Dict]: 검색 결과 리스트
    """
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not found")
        return []
    
    try:
        url = "https://google.serper.dev/search"
        
        payload = {
            "q": query,
            "num": num_results,
            "gl": "kr",  # 한국
            "hl": "ko"   # 한국어
        }
        
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 검색 결과에서 가게 이름 추출
        results = []
        
        # organic 검색 결과
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", "")
            })
        
        # local 검색 결과 (지역 비즈니스)
        for item in data.get("places", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("address", ""),
                "link": item.get("link", ""),
                "rating": item.get("rating"),
                "reviews": item.get("reviews")
            })
        
        logger.info(f"✅ Serper 검색 완료: {len(results)}개 결과")
        return results
        
    except Exception as e:
        logger.error(f"❌ Serper 검색 실패: {e}")
        return []


def extract_place_names(serper_results: List[Dict], preference: Optional[str] = None) -> List[str]:
    """
    Serper 검색 결과에서 가게 이름 추출 (개선된 필터링)
    
    Args:
        serper_results: Serper 검색 결과
        preference: 선호도 키워드 (필터링용, 예: "스테이크", "파스타")
    
    Returns:
        List[str]: 가게 이름 리스트
    """
    # 음식 카테고리별 키워드 정의
    food_keywords = {
        "스테이크": ["스테이크", "안심", "등심", "채끝", "립아이", "tomahawk"],
        "파스타": ["파스타", "스파게티", "알리오", "까르보나라", "크림", "토마토"],
        "피자": ["피자", "마르게리타", "페퍼로니", "치즈"],
        "초밥": ["초밥", "스시", "사시미", "회"],
        "라멘": ["라멘", "돈코츠", "미소", "쇼유"],
        "이자카야": ["이자카야", "사케", "안주", "꽃치"],
        "한식": ["한식", "된장", "김치", "불고기", "갈비"],
        "중식": ["중식", "짜장", "짬뽕", "탕수육", "마라"],
        "케이크": ["케이크", "디저트", "베이커리", "빵"],
        "커피": ["커피", "카페", "라떼", "아메리카노"],
    }
    
    # 제외 키워드 (카테고리별)
    exclude_map = {
        "스테이크": ["카페", "디저트", "베이커리", "버거", "파스타"],
        "파스타": ["카페", "디저트", "베이커리", "버거", "스테이크"],
        "초밥": ["카페", "디저트", "파스타", "버거"],
        "케이크": ["파스타", "스테이크", "버거", "라멘"],
        "커피": ["파스타", "스테이크", "버거", "라멘"],
    }
    
    # 선호도에 맞는 키워드 가져오기
    required_keywords = food_keywords.get(preference, [preference.lower()]) if preference else []
    exclude_keywords = exclude_map.get(preference, []) if preference else []
    
    place_names = []
    
    for result in serper_results:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        combined_text = (title + " " + snippet).lower()
        
        # 선호도 키워드 체크
        if preference:
            has_preference = any(keyword.lower() in combined_text for keyword in required_keywords)
            has_exclude = any(keyword.lower() in combined_text for keyword in exclude_keywords)
            
            # 메뉴 정보 확인 (중요!)
            menu_indicators = ["메뉴", "맛집", "유명", "인기", "추천", "리뷰", "후기"]
            has_menu_info = any(indicator in combined_text for indicator in menu_indicators)
            
            # 선호도 키워드가 없거나 제외 키워드가 있으면 스킵
            if not has_preference:
                continue
            
            # 제외 키워드가 있지만 메뉴 정보가 없으면 스킵
            if has_exclude and not has_menu_info:
                continue
        
        # 제목에서 가게 이름 추출
        cleaned_title = title.replace("- 네이버", "").replace("- 다음", "").replace("- Google", "")
        cleaned_title = cleaned_title.replace("맛집", "").replace("추천", "").replace("BEST", "")
        cleaned_title = cleaned_title.replace("베스트", "").replace("TOP", "")
        
        # 숫자 제거 (예: "1. 가게명" -> "가게명")
        import re
        cleaned_title = re.sub(r'^\d+\.?\s*', '', cleaned_title)
        cleaned_title = cleaned_title.strip()
        
        # 너무 긴 제목은 제외 (광고성)
        if len(cleaned_title) > 50 or len(cleaned_title) < 2:
            continue
        
        if cleaned_title not in place_names:
            place_names.append(cleaned_title)
            logger.info(f"   ✅ {cleaned_title} (메뉴 일치)")
    
    # 중복 제거
    place_names = list(dict.fromkeys(place_names))
    
    logger.info(f"📝 추출된 가게 이름: {len(place_names)}개")
    return place_names[:10]  # 상위 10개만
