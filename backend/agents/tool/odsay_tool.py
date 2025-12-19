"""ODsay 대중교통 경로 검색 툴 (모듈화 버전)"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from langchain_core.tools import tool
from dotenv import load_dotenv

from schemas.data_models import AgentResponse
from tools.odsay_api_tool import ODsayApiTool
from tools.odsay_parser_tool import ODsayParserTool

load_dotenv()
logger = logging.getLogger(__name__)

def _search_odsay_recursive(origin_coords: Dict, dest_coords: Dict) -> List[Dict]:
    """출발지와 도착지 간의 경로를 재귀적으로 검색하여 조정합니다."""
    api_tool = ODsayApiTool()
    
    # 1. ODsay API 호출
    result = api_tool.fetch_pub_trans_path(origin_coords, dest_coords)
    if not result:
        return []

    routes = []
    
    # 2. 시내 경로 처리 (지하철/버스)
    if 'path' in result and len(result['path']) > 0:
        for path_info in result['path'][:5]:
            # 상세 경로(Lane) 좌표 로딩
            info = path_info['info']
            map_obj = info.get('mapObj')
            lane_list = api_tool.fetch_lane_info(map_obj) if map_obj else []
            
            parsed_route = ODsayParserTool.parse_intra_city_route(
                path_info, origin_coords, dest_coords, lane_list
            )
            routes.append(parsed_route)
    
    # 시내 경로가 존재하면 즉시 반환 (직통 경로 우선)
    if routes:
        return routes

    # 3. 시외 경로 처리 (기차/고속버스)
    inter_city_options = []
    if 'trainRequest' in result: inter_city_options.extend(result['trainRequest'].get('OBJ', []))
    if 'exBusRequest' in result: inter_city_options.extend(result['exBusRequest'].get('OBJ', []))
    if 'outBusRequest' in result: inter_city_options.extend(result['outBusRequest'].get('OBJ', []))
    
    now = datetime.now()
    is_night = now.hour < 5 or now.hour >= 23 

    # 옵션 필터링 (요청되지 않은 심야 버스 등 제외)
    valid_options = []
    for opt in inter_city_options:
        bus_class = opt.get('busClass', '')
        if not is_night and '심야' in bus_class:
            continue
        valid_options.append(opt)
        
    if not valid_options:
        valid_options = inter_city_options

    # 소요 시간순 정렬 후 상위 5개 선택
    sorted_options = sorted(valid_options, key=lambda x: x.get('time', 9999))[:5]
    
    for best in sorted_options:
        start_node = {'lat': best['SY'], 'lng': best['SX'], 'formatted_address': best['startSTN']}
        end_node = {'lat': best['EY'], 'lng': best['EX'], 'formatted_address': best['endSTN']}
        
        # 연계 경로 재귀 탐색 (출발지->터미널, 터미널->도착지)
        r1 = _search_odsay_recursive(origin_coords, start_node)
        r2 = _search_odsay_recursive(end_node, dest_coords)
        
        route1 = r1[0] if r1 else None
        route2 = r2[0] if r2 else None
        
        # 구간 파싱 및 병합
        parsed_inter_route = ODsayParserTool.parse_inter_city_segment(
            best, route1, route2, origin_coords, dest_coords
        )
        routes.append(parsed_inter_route)
        
    return routes

@tool
def search_public_transport_tool(origin_search: str, destination_search: str) -> Dict[str, Any]:
    """
    ODsay API를 사용하여 출발지와 도착지 간의 '대중교통(Transit)' 경로를 검색합니다.
    시내버스, 지하철, 그리고 시외버스/기차(KTX 등)를 포함한 복합 경로를 제공합니다.
    
    Args:
        origin_search: 출발지 이름 (예: "서울역")
        destination_search: 도착지 이름 (예: "부산 해운대")
    """
    from tools.gps_tool import get_place_point 
    
    org_coords = get_place_point(origin_search)
    dst_coords = get_place_point(destination_search)
    
    if not org_coords or not dst_coords:
        return AgentResponse(success=False, agent_name="odsay", message="출발지 또는 도착지의 좌표를 찾을 수 없습니다.").dict()
    
    routes = _search_odsay_recursive(org_coords, dst_coords)
    
    if routes:
        # 결과에 원본 검색어 주입
        for r in routes:
            r['origin'] = origin_search
            r['destination'] = destination_search
            
        return AgentResponse(success=True, agent_name="odsay", data=routes, count=len(routes), message=f"경로 {len(routes)}개 검색 완료").dict()
    else:
        return AgentResponse(success=False, agent_name="odsay", message="대중교통 경로를 찾을 수 없습니다.").dict()