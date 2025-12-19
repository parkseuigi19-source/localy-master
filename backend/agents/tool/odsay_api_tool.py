"""ODsay API 통신 담당 모듈"""
import os
import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ODsayApiTool:
    def __init__(self):
        self.api_key = os.getenv("ODSAY_API_KEY")
        self.base_url = "https://api.odsay.com/v1/api"

    def fetch_lane_info(self, map_obj_id: str) -> List[List[List[float]]]:
        """ODsay 'loadLane' API를 호출하여 상세 경로 좌표를 가져옵니다"""
        if not self.api_key or not map_obj_id:
            return []
            
        try:
            url = f"{self.base_url}/loadLane"
            params = {
                'apiKey': self.api_key,
                'mapObject': '0:0@' + map_obj_id,
                'lang': 0
            }
            res = requests.get(url, params=params)
            data = res.json()
            
            lane_sections = []
            if 'result' in data and 'lane' in data['result']:
                for lane in data['result']['lane']:
                    section_coords = []
                    for section in lane.get('section', []):
                        for graph in section.get('graphPos', []):
                            section_coords.append([graph['x'], graph['y']])
                    if section_coords:
                        lane_sections.append(section_coords)
            return lane_sections
        except Exception as e:
            logger.error(f"loadLane 에러: {e}")
            return []

    def fetch_pub_trans_path(self, origin: Dict[str, float], dest: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """ODsay 'searchPubTransPath' API를 호출하여 대중교통 경로를 검색합니다"""
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/searchPubTransPath"
            params = {
                'apiKey': self.api_key,
                'SX': origin['lng'], 'SY': origin['lat'],
                'EX': dest['lng'], 'EY': dest['lat']
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return None
                
            data = response.json()
            if 'error' in data:
                return None
                
            return data.get('result')
            
        except Exception as e:
            logger.error(f"searchPubTransPath 에러: {e}")
            return None