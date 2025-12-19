"""긴급정보 멀티 툴 - Agent 연동형 (병렬 처리 최적화)"""
from langchain.tools import tool
import googlemaps
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Agent 함수 직접 임포트
from agents.emergency_agent import get_emergency_info

load_dotenv()
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_PLACES_API_KEY"))

# ========================================
# 툴 1: 통합 긴급정보 (메인)
# ========================================
@tool
def get_emergency_info_tool(region: str) -> dict:
    """
    지역 이름을 입력받아 재난, 날씨, 병원 정보가 포함된 통합 안전 리포트를 반환합니다.
    """
    result = get_emergency_info(region, include_disaster=True)
    return result.model_dump()

# ========================================
# 툴 2: 여행 계속/취소 판단
# ========================================
@tool
def travel_decision_advisor_tool(destination: str, traveler_type: str = "solo") -> dict:
    """
    목적지의 위험도 점수와 날씨를 분석하여 여행 강행/취소 여부를 조언합니다.
    """
    try:
        response = get_emergency_info(destination)
        if not response.success or not response.data:
            return {"decision": "❌ 판단 불가", "reason": "정보 수집 실패", "guide": "다시 시도해주세요."}
        
        data = response.data[0]
        risk_data = data['travel_risk']
        weather_data = data['weather']
        history_data = data['history']
        
        if not weather_data.get('api_available', False):
            return {"decision": "⚠️ 제한적 판단", "reason": "날씨 정보 누락", "risk_score": f"{risk_data['score']}/10", "guide": "기상 정보를 별도로 확인하세요."}
        
        base_risk_score = risk_data['score']
        threshold = 6
        adjusted_score = base_risk_score
        
        if traveler_type in ["family", "elderly", "child"]:
            threshold = 4; adjusted_score += 1
            safety_note = f"({traveler_type} 기준)"
        else:
            safety_note = ""
        
        reasons = []
        if weather_data.get('warnings'): reasons.append(f"기상 특보({', '.join(weather_data['warnings'])})")
        if history_data.get('recent_count', 0) > 0: reasons.append(f"최근 7일 재난 {history_data['recent_count']}건")
        if base_risk_score >= 7: reasons.append(f"높은 위험 점수 ({base_risk_score}/10)")
        
        if adjusted_score > threshold:
            decision = "STOP (취소 권장)"; emoji = "🚨"; action = risk_data.get('action', "취소 권장")
        elif 4 <= adjusted_score <= threshold:
            decision = "CAUTION (주의 필요)"; emoji = "⚠️"; action = "우산, 상비약 필수 준비"
        else:
            decision = "GO (여행 가능)"; emoji = "✅"; action = "안전한 여행 되세요!"

        specific_tips = []
        if "폭우" in str(weather_data.get('warnings')): specific_tips.append("⛈️ 계곡/하천 접근 금지")
        if "폭염" in str(weather_data.get('warnings')): specific_tips.append("🌡️ 야외 활동 자제")
        if traveler_type == "child": specific_tips.append("👶 응급실 위치 파악 필수")

        return {
            "destination": destination,
            "traveler_type": traveler_type,
            "decision": f"{emoji} {decision}",
            "risk_score": f"{adjusted_score}/10",
            "threshold": f"{threshold}/10 {safety_note}",
            "primary_reason": ", ".join(reasons) if reasons else "위험 요소 낮음",
            "detailed_guide": action,
            "specific_tips": specific_tips if specific_tips else ["특별 주의사항 없음"],
            "weather_summary": f"{weather_data.get('condition', '')}, {weather_data.get('current_temp', '?')}°C"
        }
    except Exception as e:
        return {"error": str(e), "guide": "오류가 발생했습니다."}

# ========================================
# 툴 3: 응급 상황 대응 (🚀 병렬 처리 최적화)
# ========================================
@tool
def handle_emergency_situation_tool(situation_type: str, current_location: str) -> dict:
    """
    응급 상황(부상, 사고 등) 시 가장 가까운 시설(병원/경찰서/소방서)과 이동 경로를 안내합니다.
    """
    if not gmaps: return {"error": "API 키 설정 필요"}
    
    try:
        geocode = gmaps.geocode(f"{current_location}, 대한민국", language="ko")
        if not geocode: return {"error": "위치 찾기 실패", "guide": "정확한 지역명을 입력하세요."}
        
        coords = geocode[0]['geometry']['location']
        origin = (coords['lat'], coords['lng'])
        
        # 상황별 타겟
        if situation_type in ["injury", "health", "medical"]:
            target_type = "hospital"; target_name = "응급실/병원"; emergency_call = "119"; priority = "🚨 119 구급차 요청!"
        elif situation_type in ["fire", "burn"]:
            target_type = "fire_station"; target_name = "소방서"; emergency_call = "119"; priority = "🔥 119 신고 후 대피!"
        elif situation_type in ["crime", "theft", "assault"]:
            target_type = "police"; target_name = "경찰서"; emergency_call = "112"; priority = "🚔 112 신고!"
        else:
            target_type = "hospital"; target_name = "병원"; emergency_call = "119/112"; priority = "🚨 긴급 전화 이용!"
        
        results = gmaps.places_nearby(location=origin, radius=5000, type=target_type, language="ko")
        if not results['results']:
            return {"status": "NO_FACILITY", "message": "반경 5km 내 시설 없음", "emergency_action": priority, "call": emergency_call}
        
        # 🚀 병렬 처리: 후보지들의 도보/차량 경로를 동시에 계산
        candidates = []
        
        def process_candidate(place):
            try:
                pid = place['place_id']
                dest = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
                
                # Directions API 2번 호출 (Walking + Driving)
                # 이 부분이 가장 느리므로 병렬 처리 필수
                dir_drive = gmaps.directions(origin, dest, mode="driving", language="ko")
                dir_walk = gmaps.directions(origin, dest, mode="walking", language="ko")
                
                walk_info = {}
                drive_info = {}
                
                if dir_drive:
                    leg = dir_drive[0]['legs'][0]
                    drive_info = {"dist": leg['distance']['text'], "dur": leg['duration']['text'], "val": leg['duration']['value']}
                
                if dir_walk:
                    leg = dir_walk[0]['legs'][0]
                    walk_info = {"dist": leg['distance']['text'], "dur": leg['duration']['text']}
                
                return {
                    "place_id": pid,
                    "name": place['name'],
                    "address": place.get('vicinity', ''),
                    "walk": walk_info,
                    "drive": drive_info,
                    "open_now": place.get('opening_hours', {}).get('open_now', None)
                }
            except:
                return None

        # 상위 3개 시설만 빠르게 병렬 분석
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_candidate, p) for p in results['results'][:3]]
            for future in as_completed(futures):
                res = future.result()
                if res and res.get('drive'): # 차량 경로 있는 경우만
                    candidates.append(res)
        
        if not candidates:
            return {"error": "경로 계산 실패", "action": priority, "call": emergency_call}
        
        # 차량 시간 순 정렬
        nearest = min(candidates, key=lambda x: x['drive'].get('val', 999999))
        
        map_url_drive = f"https://www.google.com/maps/dir/?api=1&destination={nearest['name']}&destination_place_id={nearest['place_id']}&travelmode=driving"
        
        status_msg = "🟢 영업 중" if nearest['open_now'] else ("🔴 휴무" if nearest['open_now'] is False else "⚪ 정보없음")

        return {
            "status": "EMERGENCY_RESPONSE",
            "priority_action": priority,
            "emergency_call": emergency_call,
            "nearest_facility": {
                "name": nearest['name'],
                "type": target_name,
                "address": nearest['address'],
                "status": status_msg,
                "by_car": f"{nearest['drive'].get('dist')} (약 {nearest['drive'].get('dur')})",
                "by_walk": f"{nearest['walk'].get('dist', '?')} (약 {nearest['walk'].get('dur', '?')})",
                "navigation": map_url_drive
            },
            "alternatives": [
                {"name": c['name'], "distance": c['drive'].get('dist')} for c in candidates if c != nearest
            ],
            "guide": "응급 상황이므로 링크를 눌러 즉시 이동하세요."
        }
        
    except Exception as e:
        return {"error": str(e), "emergency_fallback": "119/112 즉시 신고"}