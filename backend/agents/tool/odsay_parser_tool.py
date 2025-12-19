"""ODsay 데이터 파싱 및 포맷팅 담당 모듈"""
from typing import Dict, List, Any

# 지하철 색상 정보
SUBWAY_COLORS = {
    # 수도권
    '1호선': '#0052A4', '2호선': '#00A84D', '3호선': '#EF7C1C', '4호선': '#00A5DE',
    '5호선': '#996CAC', '6호선': '#CD7C2F', '7호선': '#747F00', '8호선': '#E6186C',
    '9호선': '#BDB092', '경의중앙선': '#77C4A3', '공항철도': '#0090D2', '수인분당선': '#EBA900',
    '신분당선': '#D31145', '경강선': '#0054A6', '서해선': '#8FC31F', '김포골드라인': '#A17E00',
    '우이신설선': '#B0CE18', '신림선': '#6789CA', '용인경전철': '#569733', '에버라인': '#569733',
    '의정부경전철': '#FDA600', 'GTX-A': '#9A6292',
    # 부산
    '부산1호선': '#F06A00', '부산2호선': '#81BF48', '부산3호선': '#BB8C00', '부산4호선': '#2085C5',
    '부산김해경전철': '#8652A1', '동해선': '#003DA5',
    # 대구
    '대구1호선': '#D93F5C', '대구2호선': '#00AA80', '대구3호선': '#FFB100',
    # 대전
    '대전1호선': '#007448',
    # 광주
    '광주1호선': '#009088'
}

def format_distance(meters):
    if meters >= 1000:
        return f"{meters / 1000:.2f}km"
    elif meters < 1:
        return "1m 미만"
    return f"{int(meters)}m"

def format_time(minutes):
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}시간 {mins}분" if mins > 0 else f"{hours}시간"
    elif minutes == 0:
        return "1분 미만"
    return f"{minutes}분"

class ODsayParserTool:
    @staticmethod
    def parse_intra_city_route(path_info: Dict, origin_coords: Dict, dest_coords: Dict, lane_list: List[List[List[float]]]) -> Dict:
        """단일 시내 경로 구조를 파싱합니다"""
        info = path_info['info']
        lane_idx = 0
        
        segments = []
        steps = []
        transport_summary = []
        
        subPath = path_info.get('subPath', [])
        for sub in subPath:
            trafficType = sub.get('trafficType')
            distance = sub.get('distance', 0)
            sec_time = sub.get('sectionTime', 0)
            segment_color = "#888888"
            mode_name = "도보"
            segment_path = []
            
            if trafficType == 3: # 도보
                steps.append({
                    'instruction': "도보",
                    'duration': format_time(sec_time),
                    'distance': format_distance(distance),
                    'travel_mode': 'WALKING',
                    'color': segment_color
                })
            elif trafficType == 1 or trafficType == 2: # 지하철/버스
                is_subway = (trafficType == 1)
                if is_subway:
                    lane = sub.get('lane', [{}])[0]
                    raw_name = lane.get('name', '지하철')
                    mode_name = raw_name.replace('수도권 ', '').replace('.', '')
                    
                    if mode_name in SUBWAY_COLORS:
                        segment_color = SUBWAY_COLORS[mode_name]
                    else:
                        normalized_name = mode_name.replace(' ', '')
                        if normalized_name in SUBWAY_COLORS:
                            segment_color = SUBWAY_COLORS[normalized_name]
                        else:
                            segment_color = '#0072C6'

                    transport_summary.append(mode_name)
                else:
                    lane = sub.get('lane', [{}])[0]
                    mode_name = lane.get('busNo', '버스')
                    transport_summary.append(str(mode_name))
                    segment_color = '#0068B7'
                    
                if lane_idx < len(lane_list):
                    segment_path = lane_list[lane_idx]
                    lane_idx += 1
                
                start_name = sub.get('startName','')
                end_name = sub.get('endName','')
                
                steps.append({
                    'instruction': f"{'지하철' if is_subway else '버스'} {mode_name} ({start_name} -> {end_name})",
                    'duration': format_time(sec_time),
                    'distance': format_distance(distance),
                    'travel_mode': 'TRANSIT',
                    'transit': {
                        'line_name': mode_name,
                        'departure_stop': start_name,
                        'arrival_stop': end_name,
                        'departure_coords': [sub.get('startX',0), sub.get('startY',0)]
                    },
                    'color': segment_color
                })
                
            if segment_path:
                segments.append({'type': mode_name, 'color': segment_color, 'path': segment_path})

        # 도보를 포함한 모든 구간을 연속된 경로로 연결
        final_segments = []
        if segments:
            first_pt = segments[0]['path'][0]
            final_segments.append({'type': '도보', 'color': '#888888', 'path': [[origin_coords['lng'], origin_coords['lat']], first_pt]})
            for i in range(len(segments)):
                final_segments.append(segments[i])
                if i < len(segments) - 1:
                    last_pt = segments[i]['path'][-1]
                    next_pt = segments[i+1]['path'][0]
                    if abs(last_pt[0]-next_pt[0]) > 0.00001 or abs(last_pt[1]-next_pt[1]) > 0.00001:
                        final_segments.append({'type': '도보', 'color': '#888888', 'path': [last_pt, next_pt]})
            last_pt = segments[-1]['path'][-1]
            final_segments.append({'type': '도보', 'color': '#888888', 'path': [last_pt, [dest_coords['lng'], dest_coords['lat']]]})

        return {
            'origin': origin_coords.get('formatted_address', ''),
            'destination': dest_coords.get('formatted_address', ''),
            'mode': 'transit',
            'duration': format_time(info['totalTime']),
            'distance': format_distance(info['totalDistance']),
            'cost': f"{info.get('payment', 0):,}원",
            'transport_summary': transport_summary,
            'steps': steps,
            'segments': final_segments,
            'path': [],
            'google_maps_url': ""
        }
    
    @staticmethod
    def parse_inter_city_segment(best: Dict, route1: Dict, route2: Dict, origin_coords: Dict, dest_coords: Dict) -> Dict:
        """시외 경로(접근+메인+회귀)를 조립하고 파싱합니다"""
        total_steps = []
        total_segments = []
        
        if route1:
            total_steps.extend(route1['steps'])
            total_segments.extend(route1['segments'])
        
        vehicle_type_code = best.get('type', 0)
        train_charge = best.get('charge', 0)
        bus_charge = best.get('payment', best.get('price', 0))
        
        inter_type = "시외교통"
        inter_color = '#FF5E00'
        inter_city_cost = 0

        got_name = False
        
        # 1. 기차
        if 'vehicleTypes' in best:
            vts = best['vehicleTypes']
            if isinstance(vts, list) and len(vts) > 0:
                if isinstance(vts[0], dict):
                    inter_type = vts[0].get('name', '기차')
                else:
                    inter_type = str(vts[0])
                inter_city_cost = train_charge
                got_name = True
        
        # 2. 버스
        if not got_name and 'busClass' in best:
            inter_type = best.get('busClass', '고속버스')
            if not inter_type: inter_type = "고속버스"
            inter_city_cost = bus_charge
            got_name = True

        # 3. 대체 처리 (유형 정보 부재 시 추론)
        if not got_name:
            if vehicle_type_code == 1: 
                inter_type = "기차"; inter_city_cost = train_charge
            elif vehicle_type_code == 2: 
                inter_type = "고속버스"; inter_city_cost = bus_charge
            elif vehicle_type_code == 3: 
                inter_type = "시외버스"; inter_city_cost = bus_charge
            elif vehicle_type_code == 4:
                inter_type = "항공"; inter_city_cost = bus_charge
            elif vehicle_type_code == 5:
                inter_type = "해운"; inter_city_cost = bus_charge
            else:
                if 'trainRequest' in str(best): inter_type = "기차"
                elif 'busClass' in best: inter_type = "시외버스"
                else: inter_type = "시외교통"
                inter_city_cost = max(train_charge, bus_charge)

        # 교통수단 명칭 보정
        if inter_type in ["시외교통", "기차", "1", "2"]:
            raw_str = str(best)
            if "SRT" in raw_str: inter_type = "SRT"
            elif "KTX" in raw_str: inter_type = "KTX"
            elif "새마을" in raw_str: inter_type = "새마을호"
            elif "무궁화" in raw_str: inter_type = "무궁화호"
            elif "우등" in raw_str: inter_type = "우등고속"
            elif "프리미엄" in raw_str: inter_type = "프리미엄버스"
            elif "고속" in raw_str: inter_type = "고속버스"
            elif "ITX" in raw_str: inter_type = "ITX"
        
        # 교통수단 유형에 따른 색상 지정
        if "SRT" in inter_type: inter_color = '#6F135E'
        elif "KTX" in inter_type: inter_color = '#3B57A4'
        elif "고속" in inter_type or "시외" in inter_type: inter_color = '#E94E53'
        elif "ITX" in inter_type or "새마을" in inter_type: inter_color = '#0052A4'
        elif "무궁화" in inter_type: inter_color = '#EF7C1C'
        elif "항공" in inter_type: inter_color = '#0090D2'
        
        raw_distance = best.get('distance', 0)
        if raw_distance > 1000:
            formatted_distance = format_distance(raw_distance)
        else:
            formatted_distance = f"{raw_distance:.2f}km"

        total_steps.append({
            'instruction': f"{inter_type} ({best['startSTN']} -> {best['endSTN']})",
            'duration': format_time(best.get('time', 0)),
            'distance': formatted_distance,
            'color': inter_color,
            'travel_mode': 'TRANSIT',
            'transit': {
                'line_name': inter_type,
                'departure_stop': best['startSTN'],
                'arrival_stop': best['endSTN'],
                'departure_coords': [best['SX'], best['SY']],
                'arrival_coords': [best['EX'], best['EY']]
            }
        })
        total_segments.append({
            'type': inter_type,
            'color': inter_color,
            'path': [[best['SX'], best['SY']], [best['EX'], best['EY']]]
        })
        
        if route2:
            total_steps.extend(route2['steps'])
            total_segments.extend(route2['segments'])

        # 총 비용 계산
        def parse_cost(cost_str):
            if not cost_str: return 0
            return int(str(cost_str).replace('원', '').replace(',', '').replace(' ', '').replace('(+)', ''))
            
        access_cost = parse_cost(route1.get('cost', '0')) if route1 else 0
        egress_cost = parse_cost(route2.get('cost', '0')) if route2 else 0
        total_cost = int(inter_city_cost) + access_cost + egress_cost

        # 총 거리 계산
        def parse_dist(d_str):
            if not d_str: return 0
            s = str(d_str).replace(' (+)', '').strip()
            if 'km' in s: return float(s.replace('km', '')) * 1000
            elif 'm' in s:
                if '미만' in s: return 0
                return float(s.replace('m', ''))
            return 0

        d1 = parse_dist(route1.get('distance', '0')) if route1 else 0
        d2 = parse_dist(route2.get('distance', '0')) if route2 else 0
        
        raw_d = best.get('distance', 0)
        d_inter = raw_d * 1000 if raw_d <= 1000 else raw_d
        
        total_d = d1 + d_inter + d2
        total_dist_str = format_distance(total_d)

        return {
            'origin': origin_coords.get('formatted_address', ''),
            'destination': dest_coords.get('formatted_address', ''),
            'mode': 'transit',
            'duration': format_time(best.get('time', 0)) + " (+)",
            'distance': f"{total_dist_str} (+)",
            'cost': f"{total_cost:,}원 (+)",
            'transport_summary': [inter_type],
            'steps': total_steps,
            'segments': total_segments,
            'path': [],
            'google_maps_url': ""
        }