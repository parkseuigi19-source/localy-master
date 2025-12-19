"""일정표 생성 모듈"""
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 활동별 기본 시간 (분)
ACTIVITY_DURATION = {
    'breakfast': 120,      # 2시간
    'lunch': 120,          # 2시간
    'dinner': 120,         # 2시간
    'cafe': 120,           # 2시간
    'landmark': 120,       # 2시간
    'accommodation': 30,   # 체크인 30분
}

def create_google_maps_url(origin: str, destination: str, mode: str = 'driving') -> str:
    """
    구글 맵 URL 생성
    
    Args:
        origin: 출발지
        destination: 도착지
        mode: 'driving', 'transit', 'walking'
    
    Returns:
        구글 맵 URL
    """
    origin_encoded = urllib.parse.quote(origin)
    dest_encoded = urllib.parse.quote(destination)
    
    return f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={dest_encoded}&travelmode={mode}"

def parse_time(time_str: str) -> datetime:
    """시간 문자열을 datetime으로 변환"""
    try:
        # "오전 9시", "09:00", "9시" 등 다양한 형식 지원
        time_str = time_str.replace('오전', '').replace('오후', '').replace('시', '').strip()
        
        if ':' in time_str:
            hour, minute = map(int, time_str.split(':'))
        else:
            hour = int(time_str)
            minute = 0
        
        # 오후 처리
        if '오후' in time_str and hour < 12:
            hour += 12
        
        today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        return today
    except:
        # 기본값: 오전 9시
        return datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

def format_time(dt: datetime) -> str:
    """datetime을 시간 문자열로 변환"""
    return dt.strftime("%H:%M")

def generate_daily_itinerary(day_info: Dict[str, Any]) -> str:
    """
    일차별 일정표 생성
    
    Args:
        day_info: {
            'day_number': 1,
            'date': '2025-12-13',
            'departure': {'time': '09:00', 'location': '서울역'},
            'transport_mode': 'car',  # 'car', 'transit', 'mixed'
            'destination': '부산 해운대',
            'selections': {
                'lunch': [{'name': '맛집1', 'address': '주소1'}, ...],
                'dinner': [...],
                'cafe': [...],
                'accommodation': [...],
                'landmark': [...]
            },
            'is_last_day': False,
            'return_location': '서울역'  # 마지막 날만
        }
    
    Returns:
        formatted_itinerary: 포맷된 일정표 문자열
    """
    
    day_number = day_info['day_number']
    date = day_info['date']
    departure = day_info['departure']
    transport_mode = day_info.get('transport_mode', 'car')
    destination = day_info['destination']
    selections = day_info['selections']
    is_last_day = day_info.get('is_last_day', False)
    
    # 이동 수단 매핑
    mode_map = {
        'car': 'driving',
        'transit': 'transit',
        'mixed': 'driving'
    }
    google_mode = mode_map.get(transport_mode, 'driving')
    
    # 일정표 시작
    itinerary = f"\n📅 {day_number}일차 일정표 ({date})\n"
    if is_last_day:
        itinerary += "🏁 마지막 날\n"
    itinerary += "\n"
    
    # 현재 시간 추적
    current_time = parse_time(departure['time'])
    current_location = departure['location']
    
    # 1일차: 출발 → 목적지
    if day_number == 1:
        itinerary += f"🚗 {format_time(current_time)} 출발\n"
        itinerary += f"   {current_location} → {destination}\n"
        itinerary += f"   🗺️ {create_google_maps_url(current_location, destination, google_mode)}\n"
        itinerary += f"   (이동 시간은 실제 경로에 따라 다를 수 있습니다)\n\n"
        
        # 도착 시간 추정 (4시간 30분 가정, 실제로는 GPS tool로 계산)
        current_time += timedelta(hours=4, minutes=30)
        current_location = destination
    
    # 활동 순서 (시간 순서대로)
    activities = []
    
    # 2일차 이후: 아침
    if day_number > 1:
        for item in selections.get('breakfast', []):
            activities.append(('breakfast', item))
    
    # 점심
    for item in selections.get('lunch', []):
        activities.append(('lunch', item))
    
    # 카페
    for item in selections.get('cafe', []):
        activities.append(('cafe', item))
    
    # 관광지
    for item in selections.get('landmark', []):
        activities.append(('landmark', item))
    
    # 저녁 (마지막 날 제외)
    if not is_last_day:
        for item in selections.get('dinner', []):
            activities.append(('dinner', item))
    
    # 숙소 (마지막 날 제외)
    if not is_last_day:
        for item in selections.get('accommodation', []):
            activities.append(('accommodation', item))
    
    # 각 활동 추가
    for activity_type, item in activities:
        duration = ACTIVITY_DURATION.get(activity_type, 120)
        
        # 활동 이모지
        emoji_map = {
            'breakfast': '🍳',
            'lunch': '🍽️',
            'dinner': '🍽️',
            'cafe': '☕',
            'landmark': '🗺️',
            'accommodation': '🏨'
        }
        emoji = emoji_map.get(activity_type, '📍')
        
        # 활동 이름
        name_map = {
            'breakfast': '아침',
            'lunch': '점심',
            'dinner': '저녁',
            'cafe': '카페',
            'landmark': '관광지',
            'accommodation': '숙소'
        }
        activity_name = name_map.get(activity_type, '활동')
        
        # 시작 시간
        start_time = format_time(current_time)
        end_time = format_time(current_time + timedelta(minutes=duration))
        
        itinerary += f"{emoji} {start_time}-{end_time} {activity_name} ({duration//60}시간)\n"
        itinerary += f"   {item.get('name', '장소명')}\n"
        
        if item.get('address'):
            itinerary += f"   📍 {item['address']}\n"
        
        # 이동 경로
        next_location = item.get('address') or item.get('name', destination)
        itinerary += f"   🗺️ {create_google_maps_url(current_location, next_location, 'transit')}\n\n"
        
        current_time += timedelta(minutes=duration)
        current_location = next_location
    
    # 마지막 날: 귀가
    if is_last_day and day_info.get('return_location'):
        return_location = day_info['return_location']
        itinerary += f"🚗 {format_time(current_time)} 귀가 출발\n"
        itinerary += f"   {current_location} → {return_location}\n"
        itinerary += f"   🗺️ {create_google_maps_url(current_location, return_location, google_mode)}\n"
        itinerary += f"   (귀가 시간은 실제 경로에 따라 다를 수 있습니다)\n\n"
    
    itinerary += "---\n"
    
    return itinerary
