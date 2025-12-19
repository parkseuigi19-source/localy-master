"""Serper 웹 검색 헬퍼 함수 (예약 사이트 통합)"""
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
import re

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def search_web_for_theme_accommodations(region: str, theme: str, num_results: int = 10) -> List[str]:
    """
    테마 숙소 웹 검색 (예약 사이트 우선 + 웹 검색 보완)
    
    Args:
        region: 지역 (예: "부산", "강릉")
        theme: 테마 (예: "한옥스테이", "료칸", "글램핑")
        num_results: 결과 개수
    
    Returns:
        숙소 이름 리스트
    """
    if not SERPER_API_KEY:
        print("⚠️ SERPER_API_KEY가 설정되지 않았습니다")
        return []
    
    place_names = []
    
    # 1단계: 예약 사이트 우선 검색
    booking_sites = [
        "goodchoice.kr",    # 여기어때
        "tourbis.com",      # 투어비스
        "yanolja.com",      # 야놀자
    ]
    
    for site in booking_sites:
        try:
            query = f"{region} {theme} site:{site}"
            print(f"🔍 예약 사이트 검색: {query}")
            
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "gl": "kr",
                "hl": "ko",
                "num": 5
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for result in data.get("organic", []):
                    title = result.get("title", "")
                    
                    cleaned = re.sub(r'^\d+\.?\s*', '', title)
                    cleaned = cleaned.replace('베스트', '').replace('추천', '')
                    cleaned = cleaned.replace(f' - {site}', '').strip()
                    
                    if cleaned and len(cleaned) > 2 and cleaned not in place_names:
                        place_names.append(cleaned)
                        print(f"   ✅ {cleaned} ({site})")
                
                if len(place_names) >= num_results:
                    break
        except Exception as e:
            print(f"   ⚠️ {site} 검색 실패: {e}")
    
    # 2단계: 웹 검색 보완
    if len(place_names) < num_results:
        try:
            query = f"{region} {theme} 추천"
            print(f"🔍 웹 검색 보완: {query}")
            
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "gl": "kr",
                "hl": "ko",
                "num": num_results * 2
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                theme_keywords = {
                    "료칸": ["료칸", "ryokan", "온천"],
                    "한옥스테이": ["한옥", "전통", "hanok"],
                    "글램핑": ["글램핑", "glamping"],
                    "풀빌라": ["풀빌라", "pool"],
                    "펜션": ["펜션", "pension"],
                }
                
                required_keywords = theme_keywords.get(theme, [theme.lower()])
                
                for result in data.get("organic", []):
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    combined_text = (title + " " + snippet).lower()
                    
                    has_theme = any(keyword in combined_text for keyword in required_keywords)
                    
                    if has_theme:
                        cleaned = re.sub(r'^\d+\.?\s*', '', title)
                        cleaned = cleaned.replace('베스트', '').replace('추천', '').strip()
                        
                        if cleaned and len(cleaned) > 2 and cleaned not in place_names:
                            place_names.append(cleaned)
                            print(f"   ✅ {cleaned} (웹 검색)")
        except Exception as e:
            print(f"❌ 웹 검색 실패: {e}")
    
    print(f"✅ 총 검색 결과: {len(place_names)}개")
    
    return place_names[:num_results]


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Serper 웹 검색 테스트 (예약 사이트 통합)")
    print("=" * 60)
    
    print("\n테스트: 부산 료칸")
    results = search_web_for_theme_accommodations("부산", "료칸", 5)
    print(f"\n결과: {results}\n")
