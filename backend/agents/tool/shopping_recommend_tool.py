# tools/shopping_recommend_tool.py

from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from tools.shopping_search_tool import (
    get_category_hint
)


load_dotenv()

# 추천용 LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

@tool
def recommend_shopping_tool(
    region: str,
    user_input: str,
    shopping_places: List[Dict[str, Any]],
) -> str:
    """
    [추천용 툴 - 고수준 함수]

    - 검색된 장소 리스트(최대 15개)를 입력으로 받고
    - 평점 및 리뷰 수를 반영해 상위 5개 후보만 뽑아서
    - ChatGPT로 한국어 추천 멘트를 생성
    """
    if not shopping_places:
        return f"{region}에서 해당 조건에 맞는 쇼핑 장소를 찾지 못했습니다. 😢"

    # ✅ 0. 평점 + 리뷰수를 기준으로 상위 5개 추출
    #   - rating 우선, rating 같으면 review_count 많은 순
    sorted_places = sorted(
        shopping_places,
        key=lambda s: (
            float(s.get("rating", 0) or 0),
            int(s.get("review_count", 0) or 0),
        ),
        reverse=True,
    )
    top_places = sorted_places[:5]

    # 1. 장소 리스트 텍스트 변환 (이름 + 평점 + 리뷰 + 지도 URL)
    shopping_list_text = "\n".join(
        [
            f"- {s['name']} (평점 {s['rating']}⭐, 리뷰 {s['review_count']}개)"
            f" - 지도: {s.get('map_url', 'URL 없음')}"
            for s in top_places
        ]
    )

    # 2. 카테고리 힌트
    category_hint = get_category_hint(user_input)

    # 3. 프롬프트 작성
    prompt = f"""
당신은 한국의 지역 상권을 잘 아는 쇼핑 추천 전문가입니다.

지역: {region}
카테고리(힌트): {category_hint}
사용자 입력: {user_input}

아래는 Google Places API로 조회한 상위 5개 후보 장소 목록입니다
(평점과 리뷰 수를 기준으로 선별됨):

{shopping_list_text}

요구사항:
- 한국어로 3~5문장 정도의 자연스럽고 친절한 추천 멘트를 작성하세요.
- 여러 후보 중 2~4곳 정도를 골라 각 가게의 특징(위치, 품목 다양성, 가격대, 체인/동네 가게 느낌 등)을 짧게 언급하세요.
- 사용자가 어떤 상황(퇴근 후 간단 장보기, 여행 중 생필품 구매, 약 구매 등)에서 이용하기 좋은지 맥락을 짚어주세요.
- 너무 많은 가게를 줄줄이 나열하지 말고 핵심 추천 위주로 정리하세요.
"""

    # 4. LLM 호출
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"[Shopping Recommend] LLM 호출 실패: {e}")
        fallback = (
            f"{region} 기준으로 {category_hint} 상위 {len(top_places)}곳을 찾았습니다.\n\n"
            + shopping_list_text
        )
        return fallback