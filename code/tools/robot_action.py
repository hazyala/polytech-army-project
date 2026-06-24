import streamlit as st
import requests
from langchain_core.tools import tool
from logger import get_logger

# 도구 로그 기록을 위한 로거 설정
logger = get_logger('TOOLS')

# [원격 로봇 서버 설정 - 기존 유지]
ROBOT_IP = "100.127.161.127" 
ROBOT_SERVER_URL = f"http://{ROBOT_IP}:8000/robot/action"

# [파이불렛 시뮬레이션 서버 설정 - 추가]
SIM_SERVER_URL = "http://localhost:5000/set_pos"

@tool
def robot_action(command: str, target_x_mm: float = None, target_y_mm: float = None, target_z_mm: float = None) -> str:
    """
    로봇 팔에 동작 명령을 내립니다. 
    시뮬레이터 모드인 경우 파이불렛으로, 아닌 경우 실제 로봇 서버로 전송합니다.
    
    Args:
        command: move_to_xyz
        target_x_mm: 목표 X 좌표 (mm)
        target_y_mm: 목표 Y 좌표 (mm)
        target_z_mm: 목표 Z 좌표 (mm)
    """
    try:
        # 조종판의 시뮬레이터 모드 활성화 여부를 확인합니다.
        is_sim_mode = st.session_state.get('sim_mode', False)
        
        logger.info(f"robot_action 호출 (모드: {'SIM' if is_sim_mode else 'REAL'}): {command} "
                    f"좌표: {target_x_mm}, {target_y_mm}, {target_z_mm}")

        # --- [추가] 파이불렛 시뮬레이션 모드 로직 ---
        if is_sim_mode:
            if target_x_mm is not None:
                # 파이불렛 서버는 미터(m) 단위를 사용하므로 mm를 m로 변환합니다.
                pos_m = [target_x_mm / 1000, target_y_mm / 1000, target_z_mm / 1000]
                payload = {"pos": pos_m}
                
                # 파이불렛 전령에게 명령을 전달합니다.
                response = requests.post(SIM_SERVER_URL, json=payload, timeout=2)
                
                if response.status_code == 200:
                    return f"✅ [파이불렛] 팔이 목표 좌표 {pos_m}m 로 이동하였나이다."
                else:
                    return f"❌ 파이불렛 서버 응답 실패 (코드: {response.status_code})"
            return "✅ 파이불렛 모드에서 명령을 수신했으나 좌표가 없사옵니다."

        # --- [기존 로직 유지] 실제 라즈베리 파이 서버 로직 ---
        payload = {
            "command": command,
            "target": {
                "x": target_x_mm,
                "y": target_y_mm,
                "z": target_z_mm
            } if target_x_mm is not None else None,
            "speed": 50
        }

        response = requests.post(ROBOT_SERVER_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            msg = result.get("message", "명령이 전달되었습니다.")
            return f"✅ 팔(라즈베리 파이)이 응답하였나이다: {msg} (ID: {result.get('task_id')})"
        else:
            return f"❌ 팔과의 통신에 실패하였나이다. (코드: {response.status_code})"
            
    except Exception as e:
        logger.error(f"robot_action 통신 오류: {e}")
        return f"송구하오나 마마, 팔과 연결이 닿지 않사옵니다: {str(e)}"