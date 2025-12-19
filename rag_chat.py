# backend/rag_chat.py
# ✅ 진짜 멀티 에이전트: Coordinator + Web Agent + DB Agent

import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import requests
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.memory import ConversationBufferMemory
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal
from models import Movie

load_dotenv()

chat_app = FastAPI()

# 환경 변수
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# LLM 초기화
llm = None
if OPENAI_API_KEY:
    try:
        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.7)
        print("✅ OpenAI LLM 초기화 성공")
    except Exception as e:
        print(f"⚠️ OpenAI 초기화 실패: {e}")

# Serper 초기화
search_engine = None
if SERPER_API_KEY:
    try:
        search_engine = GoogleSerperAPIWrapper()
        print("✅ Serper API 초기화 성공")
    except Exception as e:
        print(f"⚠️ Serper 초기화 실패: {e}")

# ==================== DB Agent 툴 ====================

@tool
def search_movie_in_db(title: str) -> str:
    """DB에서 영화 검색 (띄어쓰기 무시)
    
    Args:
        title: 영화 제목
    """
    db: Session = SessionLocal()
    try:
        title_no_space = title.replace(' ', '')
        
        movies = db.query(Movie).filter(
            func.replace(Movie.영화이름, ' ', '').like(f"%{title_no_space}%")
        ).limit(5).all()
        
        if not movies:
            movies = db.query(Movie).filter(
                Movie.영화이름.like(f"%{title}%")
            ).limit(5).all()
        
        if not movies:
            return f"NOT_FOUND: '{title}'"
        
        if len(movies) == 1:
            movie = movies[0]
            result = f"FOUND: {movie.영화이름}\n"
            result += f"평점: 전문가 {movie.전문가별점}/10, 관객 {movie.관객별점}/10\n"
            result += f"장르: {movie.장르}\n"
            result += f"감독: {movie.감독}\n"
            if movie.시놉시스:
                result += f"줄거리: {movie.시놉시스[:100]}...\n"
            return result
        else:
            result = f"MULTIPLE: {len(movies)}개\n"
            for movie in movies:
                result += f"- {movie.영화이름} ({movie.전문가별점}점)\n"
            return result
            
    finally:
        db.close()


@tool
def check_multiple_movies_in_db(movie_list: str) -> str:
    """여러 영화를 DB에서 일괄 확인
    
    Args:
        movie_list: 쉼표로 구분된 영화 제목들 (예: "센과 치히로,토토로,포뇨")
    """
    db: Session = SessionLocal()
    try:
        titles = [t.strip() for t in movie_list.split(',')]
        
        results = {
            "in_db": [],
            "not_in_db": []
        }
        
        for title in titles:
            title_no_space = title.replace(' ', '')
            
            movie = db.query(Movie).filter(
                func.replace(Movie.영화이름, ' ', '').like(f"%{title_no_space}%")
            ).first()
            
            if not movie:
                movie = db.query(Movie).filter(
                    Movie.영화이름.like(f"%{title}%")
                ).first()
            
            if movie:
                results["in_db"].append({
                    "title": movie.영화이름,
                    "rating": float(movie.전문가별점) if movie.전문가별점 else 0
                })
            else:
                results["not_in_db"].append(title)
        
        # 결과 포맷
        response = ""
        if results["in_db"]:
            response += "✅ DB에 있는 영화 (찜하기 가능!):\n"
            for item in sorted(results["in_db"], key=lambda x: x["rating"], reverse=True):
                response += f"- {item['title']} (⭐ {item['rating']}점)\n"
        
        if results["not_in_db"]:
            response += "\n🌐 DB에 없는 영화 (웹 정보만):\n"
            for title in results["not_in_db"]:
                response += f"- {title}\n"
        
        return response
        
    finally:
        db.close()


@tool
def get_db_movie_reviews(title: str) -> str:
    """DB 리뷰 조회"""
    db: Session = SessionLocal()
    try:
        title_no_space = title.replace(' ', '')
        movie = db.query(Movie).filter(
            func.replace(Movie.영화이름, ' ', '').like(f"%{title_no_space}%")
        ).first()
        
        if not movie:
            return f"NOT_FOUND: {title}"
        
        result = f"📰 '{movie.영화이름}' 리뷰\n\n"
        if movie.전문가내용:
            result += f"🎬 전문가: {movie.전문가내용[:200]}...\n"
        if movie.관객리뷰:
            result += f"👥 관객: {movie.관객리뷰[:200]}...\n"
        return result
        
    finally:
        db.close()


@tool
def search_movies_by_genre_in_db(genre: str) -> str:
    """DB 장르 검색"""
    db: Session = SessionLocal()
    try:
        genre_no_space = genre.replace(' ', '')
        movies = db.query(Movie).filter(
            func.replace(Movie.장르, ' ', '').like(f"%{genre_no_space}%")
        ).order_by(Movie.전문가별점.desc()).limit(10).all()
        
        if not movies:
            return f"NOT_FOUND: {genre}"
        
        result = f"✅ {genre} 영화 TOP {len(movies)}:\n"
        for i, movie in enumerate(movies, 1):
            result += f"{i}. {movie.영화이름} (⭐ {movie.전문가별점}점)\n"
        return result
        
    finally:
        db.close()


# ==================== Web Agent 툴 ====================

@tool
def search_movies_by_keyword_web(keyword: str) -> str:
    """웹에서 키워드로 영화 검색
    
    Args:
        keyword: 검색 키워드 (감독, 배우, 장르 등)
    """
    if not search_engine:
        return "ERROR: Serper API 없음"
    
    try:
        query = f"{keyword} 영화 추천 목록"
        result = search_engine.run(query)
        return f"🌐 웹 검색 결과:\n{result[:500]}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def search_popular_movies_web(year: str = "2024") -> str:
    """웹에서 인기 영화 검색"""
    if not search_engine:
        return "ERROR: Serper API 없음"
    
    try:
        query = f"{year}년 인기 영화 박스오피스"
        result = search_engine.run(query)
        return f"🔥 {year}년 인기:\n{result[:500]}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def search_movie_cast_web(title: str) -> str:
    """웹에서 배우 검색"""
    if not search_engine:
        return "ERROR: Serper API 없음"
    
    try:
        query = f"{title} 영화 배우 출연진"
        result = search_engine.run(query)
        return f"🎭 배우:\n{result[:500]}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def search_movie_details_web(title: str) -> str:
    """웹에서 영화 상세 정보"""
    if not search_engine:
        return "ERROR: Serper API 없음"
    
    try:
        query = f"{title} 영화 정보 평점 줄거리"
        result = search_engine.run(query)
        return f"🎬 정보:\n{result[:500]}"
    except Exception as e:
        return f"ERROR: {str(e)}"


# ==================== Agent 초기화 ====================

# DB Agent
DB_AGENT_PROMPT = """당신은 DB 검색 전문 Agent입니다.

역할:
- DB에서 영화 검색
- 여러 영화 일괄 확인
- 리뷰 조회
- 장르별 검색

사용 가능한 툴:
1. search_movie_in_db - 단일 영화 검색
2. check_multiple_movies_in_db - 여러 영화 일괄 확인
3. get_db_movie_reviews - 리뷰 조회
4. search_movies_by_genre_in_db - 장르 검색

답변 형식:
- 간결하고 명확하게
- "FOUND", "NOT_FOUND", "MULTIPLE" 같은 상태 포함
"""

db_agent = None
if llm:
    try:
        db_tools = [
            search_movie_in_db,
            check_multiple_movies_in_db,
            get_db_movie_reviews,
            search_movies_by_genre_in_db
        ]
        
        db_prompt = ChatPromptTemplate.from_messages([
            ("system", DB_AGENT_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        db_agent_executor = create_openai_functions_agent(llm, db_tools, db_prompt)
        db_agent = AgentExecutor(
            agent=db_agent_executor,
            tools=db_tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )
        print("✅ DB Agent 초기화 성공 (4개 툴)")
    except Exception as e:
        print(f"⚠️ DB Agent 실패: {e}")


# Web Agent
WEB_AGENT_PROMPT = """당신은 웹 검색 전문 Agent입니다.

역할:
- 웹에서 영화 검색
- 키워드/장르 추천
- 배우, 감독 정보
- 인기 영화

사용 가능한 툴:
1. search_movies_by_keyword_web - 키워드 검색
2. search_popular_movies_web - 인기 영화
3. search_movie_cast_web - 배우 검색
4. search_movie_details_web - 상세 정보

답변 형식:
- 웹 검색 결과 요약
- 영화 제목 리스트 포함
"""

web_agent = None
if llm and search_engine:
    try:
        web_tools = [
            search_movies_by_keyword_web,
            search_popular_movies_web,
            search_movie_cast_web,
            search_movie_details_web
        ]
        
        web_prompt = ChatPromptTemplate.from_messages([
            ("system", WEB_AGENT_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        web_agent_executor = create_openai_functions_agent(llm, web_tools, web_prompt)
        web_agent = AgentExecutor(
            agent=web_agent_executor,
            tools=web_tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )
        print("✅ Web Agent 초기화 성공 (4개 툴)")
    except Exception as e:
        print(f"⚠️ Web Agent 실패: {e}")


# Coordinator Agent 툴 (다른 Agent 호출)
@tool
def call_db_agent(query: str) -> str:
    """DB Agent에게 작업 위임
    
    Args:
        query: DB 검색 요청
    """
    if not db_agent:
        return "ERROR: DB Agent 없음"
    
    try:
        result = db_agent.invoke({"input": query})
        return result.get("output", "ERROR")
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def call_web_agent(query: str) -> str:
    """Web Agent에게 작업 위임
    
    Args:
        query: 웹 검색 요청
    """
    if not web_agent:
        return "ERROR: Web Agent 없음"
    
    try:
        result = web_agent.invoke({"input": query})
        return result.get("output", "ERROR")
    except Exception as e:
        return f"ERROR: {str(e)}"


# Coordinator Agent
COORDINATOR_PROMPT = """당신은 총괄 Coordinator Agent입니다.

## 역할
사용자 질문을 분석하고 적절한 Agent에게 작업을 위임합니다.

## 작업 흐름

### 1️⃣ 영화 제목 검색
예: "인터스텔라 알려줘", "기생충 있어?"
→ call_db_agent("인터스텔라 검색")

### 2️⃣ 키워드/감독/배우 검색
예: "하울의 성 감독 영화", "우주 영화 추천"
→ 2단계 실행:
  1) call_web_agent("하울의 성 감독 영화 목록")
  2) 웹에서 찾은 영화들을 call_db_agent("센과 치히로,토토로,포뇨 일괄 확인")
  3) 결과 조합하여 답변

### 3️⃣ 명시적 웹 요청
예: "웹에서 찾아줘"
→ call_web_agent만 사용

### 4️⃣ DB 전용 요청
예: "DB에 있는 SF 영화"
→ call_db_agent만 사용

## 중요!
- 키워드/감독 검색 시 반드시 웹 → DB 순서로!
- 웹에서 찾은 영화 목록을 DB에서 일괄 확인!
- DB에 있는 것 우선 표시!

## 응답 형식
✅ DB에 있는 영화: (찜하기 가능)
🌐 웹 정보: (참고용)
"""

coordinator_agent = None
if llm:
    try:
        coordinator_tools = [
            call_db_agent,
            call_web_agent
        ]
        
        coordinator_prompt = ChatPromptTemplate.from_messages([
            ("system", COORDINATOR_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        coordinator_executor = create_openai_functions_agent(llm, coordinator_tools, coordinator_prompt)
        coordinator_agent = AgentExecutor(
            agent=coordinator_executor,
            tools=coordinator_tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
        print("✅ Coordinator Agent 초기화 성공")
        print("   📍 3-Agent 구조: Coordinator → DB/Web")
    except Exception as e:
        print(f"⚠️ Coordinator 실패: {e}")


# Memory
conversation_memories = {}


# ==================== FastAPI Startup ====================

@chat_app.on_event("startup")
async def startup_event():
    """FastAPI startup 이벤트"""
    print("🚀 3-Agent 시스템 시작")
    print("   📍 Coordinator → DB/Web Agents")
    if llm:
        print("✅ OpenAI LLM 준비")
    if search_engine:
        print("✅ Serper API 준비")
    if coordinator_agent:
        print("✅ Coordinator 준비")
    if db_agent:
        print("✅ DB Agent 준비")
    if web_agent:
        print("✅ Web Agent 준비")


# ==================== FastAPI 엔드포인트 ====================

class Query(BaseModel):
    message: str
    user_id: Optional[str] = "web_user"
    session_id: Optional[str] = None


@chat_app.post("/chat")
def chat(query: Query):
    """영화 추천 챗봇 (3-Agent 구조)"""
    if not coordinator_agent:
        return {"response": "Agent가 초기화되지 않았습니다.", "error": True}
    
    try:
        session_id = query.session_id or query.user_id or "default"
        
        if session_id not in conversation_memories:
            conversation_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        
        memory = conversation_memories[session_id]
        
        result = coordinator_agent.invoke({
            "input": query.message,
            "chat_history": memory.chat_memory.messages
        })
        
        response = result.get("output", "응답 생성 실패")
        
        memory.save_context(
            {"input": query.message},
            {"output": response}
        )
        
        return {"response": response, "success": True}
    except Exception as e:
        error_msg = f"오류 발생: {str(e)}"
        print(f"❌ Agent 에러: {e}")
        return {"response": error_msg, "error": True}


@chat_app.get("/")
def root():
    return {
        "status": "running",
        "architecture": "Multi-Agent System (3 Agents)",
        "agents": {
            "coordinator": "총괄 (Agent 선택)",
            "db_agent": "DB 검색 (4 tools)",
            "web_agent": "웹 검색 (4 tools)"
        },
        "flow": "Coordinator → DB/Web → 결과 조합",
        "openai": llm is not None,
        "serper": search_engine is not None,
        "db_agent_ready": db_agent is not None,
        "web_agent_ready": web_agent is not None,
        "coordinator_ready": coordinator_agent is not None
    }


@chat_app.get("/test")
def test():
    """Agent 테스트"""
    if not coordinator_agent:
        return {"error": "Agent 미초기화"}
    
    test_query = "하울의 성 감독 영화 추천해줘"
    
    try:
        result = coordinator_agent.invoke({
            "input": test_query,
            "chat_history": []
        })
        return {
            "query": test_query,
            "response": result.get("output", "")[:500]
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(chat_app, host="0.0.0.0", port=8001)
