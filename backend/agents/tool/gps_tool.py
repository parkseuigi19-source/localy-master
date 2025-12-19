"""네이버 지도 기반 장소 검색 및 자동차 경로 검색 툴"""
import os
import logging
import requests
import urllib.parse
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from dotenv import load_dotenv
from schemas.data_models import AgentResponse

load_dotenv()
logger = logging.getLogger(__name__)

def _get_naver_geocode(address: str, client_id: str, client_secret: str) -> Optional[Dict]:
    """[내부함수] 네이버 Geocoding API로 주소를 좌표로 변환"""
    try:
        url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        headers = {
            "x-ncp-apigw-api-key-id": client_id,
            "x-ncp-apigw-api-key": client_secret
        }
        params = {"query": address}
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get('status') == 'OK' and data.get('addresses'):
            item = data['addresses'][0]
            return {
                'lat': float(item['y']),
                'lng': float(item['x']),
                'formatted_address': item['roadAddress'] or item['jibunAddress']
            }
        return None
    except Exception as e:
        logger.error(f"네이버 Geocoding 에러: {e}")
        return None

def get_place_point(query: str) -> Optional[Dict]:
    """
    [공용함수] 장소명 -> 좌표 변환 (하이브리드 방식)
    다른 툴에서도 좌표가 필요할 때 사용할 수 있도록 일반 함수로 유지합니다.
    """
    try:
        # 1. Search API (장소명 -> 주소)
        search_id = os.getenv('NAVER_SEARCH_ID')
        search_secret = os.getenv('NAVER_SEARCH_SECRET')
        
        if search_id and search_secret:
            encText = urllib.parse.quote(query)
            # 지역 코드를 제거하고 검색 (예: "서울 강남역" -> "강남역") 네이버 검색 품질을 위해
            url = f"https://openapi.naver.com/v1/search/local.json?query={encText}&display=1"
            headers = {
                "X-Naver-Client-Id": search_id,
                "X-Naver-Client-Secret": search_secret
            }
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                items = res.json().get('items', [])
                if items:
                    address = items[0]['roadAddress'] or items[0]['address']
                    # 태그 제거
                    title = items[0]['title'].replace('<b>', '').replace('</b>', '')
                    logger.info(f"🔍 '{query}' -> '{title}' ({address})")
                    # 여기서 찾은 주소로 query를 교체
                    query = address

        # 2. Geocoding API (주소 -> 좌표)
        client_id = os.getenv('NAVER_CLIENT_ID')
        client_secret = os.getenv('NAVER_CLIENT_SECRET')
        return _get_naver_geocode(query, client_id, client_secret)
        
    except Exception as e:
        logger.error(f"장소 검색 에러: {e}")
        return None

@tool
def search_place_tool(query: str) -> Dict[str, Any]:
    """
    장소(POI) 이름이나 주소를 입력받아 정확한 위도/경도 좌표와 도로명 주소를 반환합니다.
    경로 검색 전에 출발지와 도착지의 좌표를 얻기 위해 사용해야 합니다.
    """
    result = get_place_point(query)
    if result:
        return {"success": True, "data": result}
    else:
        return {"success": False, "message": "장소를 찾을 수 없습니다."}

@tool
def search_driving_route_tool(origin_search: str, destination_search: str) -> Dict[str, Any]:
    """
    네이버 지도를 사용하여 출발지와 도착지 간의 '자동차(Driving)' 경로를 검색합니다.
    대중교통이 아닌 자가용/택시 이동 경로가 필요할 때 사용합니다.
    
    Args:
        origin_search: 출발지 검색어 (예: "강남역")
        destination_search: 도착지 검색어 (예: "속초 해수욕장")
    """
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return AgentResponse(success=False, agent_name="gps", message="네이버 API 키가 설정되지 않았습니다.").dict()
    
    try:
        origin_geo = get_place_point(origin_search)
        dest_geo = get_place_point(destination_search)
        
        if not origin_geo:
            return AgentResponse(success=False, agent_name="gps", message=f"출발지('{origin_search}')를 찾을 수 없습니다.").dict()
        if not dest_geo:
            return AgentResponse(success=False, agent_name="gps", message=f"도착지('{destination_search}')를 찾을 수 없습니다.").dict()
        
        start_loc = origin_geo
        end_loc = dest_geo
        
        # 네이버 Directions API 호출
        url = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
        headers = {
            "x-ncp-apigw-api-key-id": client_id,
            "x-ncp-apigw-api-key": client_secret
        }
        params = {
            "start": f"{start_loc['lng']},{start_loc['lat']}",
            "goal": f"{end_loc['lng']},{end_loc['lat']}",
            "option": "trafast"
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # 에러 체크
        if 'error' in data:
            error_msg = data['error'].get('message', '알 수 없는 오류')
            return AgentResponse(success=False, agent_name="gps", message=f"네이버 API 에러: {error_msg}").dict()
        
        if data.get('code') != 0:
            return AgentResponse(success=False, agent_name="gps", message=f"경로 검색 실패 (Code: {data.get('code')})").dict()
        
        if 'route' in data and 'trafast' in data['route']:
            route_data = data['route']['trafast'][0]
            summary = route_data['summary']
            
            duration_mins = summary['duration'] // 60 // 1000
            distance_km = summary['distance'] / 1000
            toll_fare = summary.get('tollFare', 0)
            fuel_price = summary.get('fuelPrice', 0)
            total_cost = toll_fare + fuel_price
            
            hours = duration_mins // 60
            mins = duration_mins % 60
            duration_text = f"{hours}시간 {mins}분" if hours > 0 else f"{mins}분"
            
            # 네이버 맵 URL
            sname = urllib.parse.quote(origin_search)
            ename = urllib.parse.quote(destination_search)
            naver_url = f"https://map.naver.com/p/directions/{start_loc['lng']},{start_loc['lat']},{sname},,GEO/{end_loc['lng']},{end_loc['lat']},{ename},,GEO/-/car"
            
            routes_found = [{
                'origin': origin_geo['formatted_address'],
                'destination': dest_geo['formatted_address'],
                'mode': 'driving',
                'duration': duration_text,
                'distance': f"{distance_km:.1f} km",
                'cost': f"{total_cost:,}원 (톨비+주유)",
                'transport_summary': ['자동차'],
                'steps': [{'instruction': f"자동차로 {duration_text} 소요", 'duration': duration_text, 'distance': f"{distance_km:.1f} km", 'travel_mode': 'DRIVING'}],
                'path': route_data.get('path', []),
                'google_maps_url': naver_url
            }]
            
            return AgentResponse(success=True, agent_name="gps", data=routes_found, message="네이버 자동차 경로 검색 완료", count=1).dict()
            
        return AgentResponse(success=False, agent_name="gps", message="경로를 찾을 수 없습니다.").dict()

    except Exception as e:
        logger.error(f"네이버 API 에러: {e}")
        return AgentResponse(success=False, agent_name="gps", message=f"에러 발생: {str(e)}").dict()