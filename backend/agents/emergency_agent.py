"""긴급정보 에이전트 - 병렬 처리 최적화 (Speed Up)"""
import os
import sys
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import googlemaps
from schemas.data_models import PlaceData, AgentResponse

load_dotenv()

# 로깅 설정 (불필요한 로그는 줄임)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
# 로거 레벨 조정
logger.setLevel(logging.INFO)

# httpx, openai 로그 끄기
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# API 키 확인
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
DATA_GO_API_KEY = os.getenv("DATA_GO_KR_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

gmaps = googlemaps.Client(key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

# --- 1. 재난문자 조회 ---
def fetch_disaster_alerts(region: str) -> List[Dict[str, Any]]:
    if not DATA_GO_API_KEY: return []
    
    # logger.info(f"⚡ 재난문자 조회 시작: {region}") # 로그 줄임
    
    try:
        url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247"
        params = {
            "serviceKey": DATA_GO_API_KEY,
            "returnType": "json",
            "pageNo": "1",
            "numOfRows": "100",
            "rgnNm": region
        }
        # 타임아웃을 짧게 설정하여 전체 프로세스 지연 방지
        response = requests.get(url, params=params, timeout=3)
        
        if response.status_code != 200: return []
        
        try:
            data = response.json()
        except:
            return []
            
        items = data.get("body", data.get("data", [])) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if items is None: items = []

        alerts = []
        for item in items:
            raw_date = item.get("CRT_DT", "")
            try:
                clean_date = raw_date.replace("-", "").replace("/", "").replace(" ", "")[:8]
                parsed_date = datetime.strptime(clean_date, "%Y%m%d") if len(clean_date) == 8 else None
            except:
                parsed_date = None
            
            alerts.append({
                "type": item.get("EMRG_STEP_NM", "재난문자"),
                "date": raw_date,
                "parsed_date": parsed_date,
                "location": item.get("RCPTN_RGN_NM", ""),
                "message": item.get("MSG_CN", "")
            })
        
        alerts.sort(key=lambda x: x['date'], reverse=True)
        return alerts
    except:
        return []

# --- 2. 날씨 및 옷차림 추천 ---
def fetch_weather_and_outfit(region: str) -> Dict[str, Any]:
    if not OPENWEATHER_API_KEY or not gmaps:
        return {"api_available": False, "condition": "설정 오류", "warnings": [], "risk_level": 0}
    
    # logger.info(f"⚡ 날씨 조회 시작: {region}")
    
    try:
        geocode = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode:
            return {"api_available": False, "condition": "지역불명", "warnings": [], "risk_level": 0}
        
        coords = geocode[0]['geometry']['location']
        
        url = "https://api.openweathermap.org/data/2.5/forecast"
        res = requests.get(url, params={
            'lat': coords['lat'],
            'lon': coords['lng'],
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'kr'
        }, timeout=3)
        
        if res.status_code != 200:
            return {"api_available": False, "condition": "API 오류", "warnings": [], "risk_level": 0}
        
        data = res.json()
        current = data['list'][0]
        
        # 데이터 추출 (기존 로직 동일)
        temp_now = current['main']['temp']
        temp_feels = current['main']['feels_like']
        humidity = current['main']['humidity']
        wind_speed = current['wind']['speed']
        condition = current['weather'][0]['description']
        temps_24h = [item['main']['temp'] for item in data['list'][:8]]
        temp_min, temp_max = min(temps_24h), max(temps_24h)
        
        # 옷차림 로직
        outfit = ""
        if temp_now >= 28: outfit = "🎽 민소매, 반바지 (매우 더움)"
        elif 23 <= temp_now < 28: outfit = "👕 반팔, 얇은 셔츠"
        elif 20 <= temp_now < 23: outfit = "👚 긴팔티, 가디건"
        elif 17 <= temp_now < 20: outfit = "🧥 니트, 맨투맨, 청바지"
        elif 12 <= temp_now < 17: outfit = "🧥 자켓, 야상, 스타킹"
        elif 9 <= temp_now < 12: outfit = "🧥 트렌치코트, 기모바지"
        elif 5 <= temp_now < 9: outfit = "🧥 코트, 가죽자켓, 히트텍"
        else: outfit = "🧣 패딩, 목도리, 장갑 (매우 추움)"

        # 위험 요소 체크
        warnings = []
        risk_level = 0
        for item in data['list'][:8]:
            rain = item.get('rain', {}).get('3h', 0)
            temp = item['main']['temp']
            wind = item['wind']['speed']

            if rain > 50: 
                warnings.append("⚠️ 폭우 경보"); risk_level = max(risk_level, 8)
            elif rain > 20: 
                warnings.append("🌧️ 강한 비"); risk_level = max(risk_level, 5)
            
            if temp > 35: 
                warnings.append("🔥 폭염 경보"); risk_level = max(risk_level, 7)
            elif temp > 33: 
                warnings.append("🌡️ 폭염주의보"); risk_level = max(risk_level, 5)
            
            if temp < -15: 
                warnings.append("🧊 한파 경보"); risk_level = max(risk_level, 7)
            elif temp < -10: 
                warnings.append("❄️ 한파주의보"); risk_level = max(risk_level, 5)
            
            if wind > 14: 
                warnings.append("🌪️ 강풍 주의"); risk_level = max(risk_level, 4)

        return {
            "current_temp": round(temp_now, 1),
            "feels_like": round(temp_feels, 1),
            "min_temp": round(temp_min, 1),
            "max_temp": round(temp_max, 1),
            "humidity": humidity,
            "wind_speed": round(wind_speed, 1),
            "condition": condition,
            "outfit": outfit,
            "warnings": list(set(warnings)),
            "risk_level": risk_level,
            "api_available": True
        }
    except:
        return {"api_available": False, "condition": "에러", "warnings": [], "risk_level": 0}

# --- 3. 6개월 위험 이력 (로직 동일) ---
def analyze_risk_history(alerts: List[Dict]) -> Dict[str, Any]:
    if not alerts:
        return {"summary": "이력 없음", "risk_score": 0, "recent_count": 0, "total_count": 0, "detail": "최근 6개월 재난문자 없음"}
    
    now = datetime.now()
    six_mo_ago = now - timedelta(days=180)
    one_mo_ago = now - timedelta(days=30)
    one_week_ago = now - timedelta(days=7)
    
    counts = {"화재": 0, "산불": 0, "지진": 0, "호우": 0, "태풍": 0, "대설": 0, "폭염": 0}
    recent_7d = 0
    recent_30d = 0
    total_valid = 0
    
    for a in alerts:
        parsed_date = a.get('parsed_date')
        if not parsed_date or parsed_date < six_mo_ago: continue
        
        total_valid += 1
        if parsed_date >= one_week_ago: recent_7d += 1
        if parsed_date >= one_mo_ago: recent_30d += 1
        
        msg = a['message']
        for k in counts:
            if k in msg: counts[k] += 1
    
    risk_score = 0
    risk_score += recent_7d * 3
    risk_score += (recent_30d - recent_7d) * 2
    risk_score += (total_valid - recent_30d) * 0.5
    risk_score += counts['지진'] * 4 + counts['산불'] * 2 + counts['태풍'] * 2
    risk_score = min(10, int(risk_score))
    
    summary_parts = [f"{k} {v}건" for k, v in counts.items() if v > 0]
    
    return {
        "summary": ", ".join(summary_parts[:3]) if summary_parts else "특이사항 없음",
        "risk_score": risk_score,
        "recent_count": recent_7d,
        "total_count": total_valid,
        "detail": f"최근 7일 {recent_7d}건, 30일 {recent_30d}건, 6개월 {total_valid}건"
    }

# --- 4. 긴급 시설 검색 (🚀 병렬 처리 최적화) ---
def find_emergency_services(region: str) -> List[PlaceData]:
    if not gmaps: return []
    
    # logger.info(f"⚡ 긴급 시설 검색 시작: {region}")
    
    try:
        geocode = gmaps.geocode(f"{region}, 대한민국", language="ko")
        if not geocode: return []
        
        coords = geocode[0]['geometry']['location']
        origin = (coords['lat'], coords['lng'])
        
        targets = [
            ("hospital", "종합병원", 2),
            ("pharmacy", "약국", 1),
            ("police", "경찰서", 1),
            ("fire_station", "소방서", 1),
        ]
        
        places_found = []
        
        # 1. 내부 함수: 검색 및 거리 계산을 한 번에 처리 (병렬 실행용)
        def process_target(target_type, target_name, limit):
            try:
                res = gmaps.places_nearby(
                    location=origin, radius=3000, type=target_type, language="ko"
                )
                local_places = []
                for p in res['results'][:limit]:
                    pid = p['place_id']
                    dest = (p['geometry']['location']['lat'], p['geometry']['location']['lng'])
                    
                    # 거리 계산 (Directions API도 네트워크 요청이므로 여기서 수행)
                    distance = "계산불가"
                    duration = "계산불가"
                    try:
                        directions = gmaps.directions(origin, dest, mode="driving", language="ko")
                        if directions:
                            leg = directions[0]['legs'][0]
                            distance = leg['distance']['text']
                            duration = leg['duration']['text']
                    except:
                        pass
                    
                    open_now = p.get('opening_hours', {}).get('open_now', None)
                    google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{pid}"
                    
                    local_places.append(PlaceData(
                        place_id=pid,
                        name=p['name'],
                        category=target_name,
                        address=p.get('vicinity', ''),
                        region=region,
                        latitude=p['geometry']['location']['lat'],
                        longitude=p['geometry']['location']['lng'],
                        open_now=open_now,
                        google_maps_url=google_maps_url,
                        tags=[target_name, f"거리:{distance}", f"시간:{duration}"]
                    ))
                return local_places
            except:
                return []

        # 2. 병렬 실행: 시설 종류별로 동시에 검색+거리계산
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_target, t[0], t[1], t[2]) for t in targets]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    places_found.extend(result)
        
        return places_found
        
    except Exception as e:
        logger.error(f"시설 검색 실패: {e}")
        return []

# --- 5. 종합 위험도 계산 (로직 동일) ---
def calculate_travel_risk_score(weather_risk, history_risk, alerts_count, recent_alerts, current_temp=None):
    score = 0
    score += weather_risk * 0.5 + history_risk * 0.2
    score += min(alerts_count, 10) * 0.2 + recent_alerts * 0.5
    
    current_month = datetime.now().month
    if 6 <= current_month <= 8:
        if current_temp and current_temp > 33: score += 1.5
        if history_risk >= 5: score += 1
    elif current_month in [12, 1, 2]:
        if current_temp and current_temp < -5: score += 1.5
        if history_risk >= 5: score += 1
    else:
        if history_risk >= 3: score += 0.5
    
    score = min(10, int(score))
    
    if score <= 2: return {"score": score, "level": "안전", "emoji": "✅", "msg": "여행하기 좋은 상태입니다.", "action": "즐거운 여행 되세요!"}
    elif score <= 5: return {"score": score, "level": "주의", "emoji": "⚠️", "msg": "날씨나 주변 상황을 확인하세요.", "action": "우산, 상비약 등 기본 준비물을 챙기세요."}
    elif score <= 7: return {"score": score, "level": "경고", "emoji": "🚫", "msg": "여행 연기를 권장합니다.", "action": "실내 활동 위주로 변경하거나 일정을 조정하세요."}
    else: return {"score": score, "level": "위험", "emoji": "🚨", "msg": "매우 위험합니다. 취소하세요.", "action": "즉시 안전한 장소로 이동하고, 여행은 반드시 취소하세요."}

# --- 메인 통합 함수 (🚀 전체 병렬화) ---
def get_emergency_info(region: str, include_disaster: bool = True) -> AgentResponse:
    logger.info(f"⚡ [병렬 실행] 긴급 정보 조회 시작: {region}")
    
    try:
        # 1. 3가지 메인 작업 동시 실행 (재난 / 날씨 / 시설)
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_alerts = executor.submit(fetch_disaster_alerts, region) if include_disaster else None
            future_weather = executor.submit(fetch_weather_and_outfit, region)
            future_facilities = executor.submit(find_emergency_services, region)
            
            # 결과 대기 및 수집
            alerts = future_alerts.result() if future_alerts else []
            weather = future_weather.result()
            facilities = future_facilities.result()

        # 2. 동기 처리 (계산 로직은 매우 빠름)
        history = analyze_risk_history(alerts)
        risk = calculate_travel_risk_score(
            weather_risk=weather.get('risk_level', 0),
            history_risk=history.get('risk_score', 0),
            alerts_count=len(alerts),
            recent_alerts=history.get('recent_count', 0),
            current_temp=weather.get('current_temp')
        )
        
        # 3. 메시지 생성
        msg = f"[{region} 안전 리포트 {risk['emoji']}]\n"
        msg += f"등급: {risk['level']} (점수: {risk['score']}/10)\n"
        msg += f"💡 조언: {risk['action']}\n\n"
        
        if weather.get('api_available'):
            msg += f"🌤️ 날씨: {weather['condition']}, {weather['current_temp']}°C"
            msg += f" (체감 {weather['feels_like']}°C)\n"
            msg += f"   습도 {weather['humidity']}%, 풍속 {weather['wind_speed']}m/s\n"
            msg += f"👕 추천: {weather['outfit']}\n"
            if weather['warnings']: msg += f"⚠️ 특이사항: {', '.join(weather['warnings'])}\n"
        else:
            msg += "🌤️ 날씨: 정보를 가져올 수 없습니다.\n"
        
        if alerts:
            msg += f"\n📢 재난알림: {history['detail']}\n   {history['summary']}\n"
        else:
            msg += "\n📢 재난알림: 최근 6개월 이내 재난문자 없음\n"
        
        if facilities:
            msg += f"\n🏥 주변 긴급 시설 ({len(facilities)}곳)\n"
            for p in facilities:
                status = "🟢 영업 중" if p.open_now else ("🔴 휴무" if p.open_now is False else "⚪ 정보 없음")
                distance = next((t for t in p.tags if "거리:" in t), "거리 정보 없음")
                duration = next((t for t in p.tags if "시간:" in t), "")
                msg += f"- {p.name} ({p.category}) {status}\n"
                msg += f"   📍 {p.address}\n"
                msg += f"   🚗 {distance} ({duration})\n"
                msg += f"   🔗 {p.google_maps_url}\n\n"
        else:
            msg += "\n🏥 주변 긴급 시설: 검색된 곳 없음\n"

        logger.info(f"✅ 조회 완료: {region}")

        return AgentResponse(
            success=True,
            agent_name="emergency",
            data=[{
                "region": region,
                "travel_risk": risk,
                "weather": weather,
                "alerts": alerts,
                "history": history,
                "facilities": [p.model_dump() for p in facilities]
            }],
            count=1,
            message=msg
        )
        
    except Exception as e:
        logger.error(f"긴급 정보 조회 실패: {e}")
        return AgentResponse(success=False, agent_name="emergency", message=f"오류 발생: {str(e)}", error=str(e))

# ==========================================================
# 🔥 [셀프 테스트] (삭제 금지)
# ==========================================================
if __name__ == "__main__":
    import time
    start = time.time()
    
    print("\n" + "█" * 60)
    print("🚨 긴급 정보 에이전트 (Self-Test: 병렬 처리)")
    print("▔" * 60 + "\n")
    
    test_region = "서울"
    print(f"📍 '{test_region}' 정보 조회 중... \n")
    
    result = get_emergency_info(test_region, include_disaster=True)
    
    end = time.time()
    print(f"\n⏱️ 소요 시간: {round(end-start, 2)}초 (최적화됨)")
    
    if result.success:
        print("\n" + "="*60)
        print("📝 [최종 리포트 메시지]")
        print("="*60)
        print(result.message)
    else:
        print(f"❌ 실패: {result.message}")