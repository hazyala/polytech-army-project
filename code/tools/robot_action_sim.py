import streamlit as st
import math
from langchain_core.tools import tool
from logger import get_logger

# 도구의 동작 상태 및 오류를 기록하기 위한 로거
logger = get_logger('TOOLS')

# [로봇 물리 제원 설정 - 단위: Meters]
LINK_L1 = 0.08      # 어깨에서 팔꿈치까지 (J2~J3)
LINK_L2 = 0.08      # 팔꿈치에서 손목까지 (J3~J4)
LINK_D = 0.19       # 손목에서 그리퍼 끝단까지 (J4~End)
BASE_HEIGHT = 0.12  # 지면에서 J2 관절까지의 높이
TOTAL_REACH = LINK_L1 + LINK_L2 + LINK_D # 총 가동 범위: 0.35m

# [카메라 설치 오프셋 설정 - 단위: Meters]
# 로봇 베이스 중심(0,0,0) 기준 카메라의 상대 위치
CAM_OFFSET_X = -0.05 # 로봇보다 5cm 뒤에 위치
CAM_OFFSET_Y = 0.0   # 로봇과 좌우 정렬됨
CAM_OFFSET_Z = 0.10  # 로봇 베이스보다 10cm 높게 위치

def solve_inverse_kinematics(x_m, y_m, z_m):
    """
    3차원 좌표를 5축 로봇의 관절 각도로 변환합니다.
    그리퍼(D) 길이까지 포함하여 도달 가능 여부를 판단합니다.
    """
    try:
        # 1. J1: 베이스 수평 회전각 (atan2 사용)
        joint1 = math.degrees(math.atan2(y_m, x_m))
        
        # 2. 로봇 베이스(J2) 기준 목표 높이(z)와 수평 거리(r)
        r_target = math.sqrt(x_m**2 + y_m**2)
        z_target = z_m - BASE_HEIGHT
        
        # 전체 도달 거리 검증 (피타고라스 정리)
        dist_to_target = math.sqrt(r_target**2 + z_target**2)
        if dist_to_target > TOTAL_REACH:
            return None # 물리적으로 닿지 않는 곳

        # 3. 그리퍼(D) 접근 각도(phi) 계산
        # 목표 지점을 향해 팔을 뻗도록 유동적으로 설정
        phi_rad = math.atan2(z_target, r_target)
        
        # 손목 위치(J4) 추정
        r_wrist = r_target - LINK_D * math.cos(phi_rad)
        z_wrist = z_target - LINK_D * math.sin(phi_rad)
        
        # 4. L1, L2 구간에 대한 코사인 법칙 적용
        dist_sq = r_wrist**2 + z_wrist**2
        dist = math.sqrt(dist_sq)
        
        # 손목 위치까지 도달 가능한지 재검증
        if dist > (LINK_L1 + LINK_L2):
            return None

        # J3(팔꿈치) 각도 계산
        cos_j3 = (dist_sq - LINK_L1**2 - LINK_L2**2) / (2 * LINK_L1 * LINK_L2)
        joint3_rad = math.acos(max(-1, min(1, cos_j3)))
        
        # J2(어깨) 각도 계산
        alpha = math.atan2(z_wrist, r_wrist)
        beta = math.acos(max(-1, min(1, (LINK_L1**2 + dist_sq - LINK_L2**2) / (2 * LINK_L1 * dist))))
        
        # 90도 오프셋 보정 적용 (마마의 교시 준수)
        j2_final = math.degrees(alpha + beta) - 90.0
        j3_final = math.degrees(joint3_rad) - 90.0
        # 말단 그리퍼가 수평을 유지하거나 목표를 향하도록 설정
        j4_final = math.degrees(phi_rad) - (j2_final + 90.0) - (j3_final + 90.0)
        
        return {
            "J1": round(joint1, 1), 
            "J2": round(j2_final, 1), 
            "J3": round(j3_final, 1), 
            "J4": round(j4_final, 1), 
            "J5": 0.0
        }
    except Exception:
        return None

@tool
def robot_action(command: str, target_x_cm: float = None, target_y_cm: float = None, target_z_cm: float = None) -> str:
    """
    카메라 좌표를 로봇 좌표로 번역하여 점진적으로 이동시키고 각 관절 각도를 산출합니다.
    """
    try:
        # 좌표값이 없는 단순 명령 처리
        if target_x_cm is None:
            return f"[{command}] 시뮬레이션 동작을 수행하였나이다."

        # [1단계] 카메라 좌표계(Vision) -> 로봇 좌표계(Robot) 번역
        # 로봇 X = 카메라 Z + Offset / 로봇 Y = -카메라 X / 로봇 Z = -카메라 Y + Offset
        v_x, v_y, v_z = target_x_cm / 100.0, target_y_cm / 100.0, target_z_cm / 100.0
        robot_target_x = v_z + CAM_OFFSET_X
        robot_target_y = -v_x + CAM_OFFSET_Y
        robot_target_z = -v_y + CAM_OFFSET_Z
        
        # [2단계] 로봇의 가상 현재 위치 관리 (Streamlit 세션 활용)
        if "current_arm_pos" not in st.session_state:
            # 초기 대기 위치 (로봇 기준 좌표)
            st.session_state.current_arm_pos = {"x": 0.05, "y": 0.0, "z": 0.12}

        curr = st.session_state.current_arm_pos
        
        # 목표 지점까지의 벡터 및 직선 거리 계산
        diff_x = robot_target_x - curr['x']
        diff_y = robot_target_y - curr['y']
        diff_z = robot_target_z - curr['z']
        total_dist = math.sqrt(diff_x**2 + diff_y**2 + diff_z**2)

        # 최종 도달 판정 (0.5cm 이내)
        if total_dist < 0.005:
            final_angles = solve_inverse_kinematics(curr['x'], curr['y'], curr['z'])
            return f"마마, 안착하였나이다! 최종 각도: {final_angles}. 시뮬레이션 종료."

        # [3단계] 지능형 보폭 결정 (10cm 기준 5cm 또는 1cm)
        step_size = 0.05 if total_dist > 0.10 else 0.01
        step_scale = min(step_size / total_dist, 1.0)
        
        # 위치 업데이트
        new_pos = {
            "x": curr['x'] + (diff_x * step_scale),
            "y": curr['y'] + (diff_y * step_scale),
            "z": curr['z'] + (diff_z * step_scale)
        }
        st.session_state.current_arm_pos = new_pos
        
        # 현재 위치에 대한 역기구학 각도 계산
        angles = solve_inverse_kinematics(new_pos['x'], new_pos['y'], new_pos['z'])
        
        # [4단계] 결과 보고
        angle_info = f"산출 각도: {angles}" if angles else "팔이 닿지 않는 무리한 위치이옵니다"
        remaining_cm = (total_dist - step_size) * 100

        return (f"현재 로봇 좌표 ({new_pos['x']*100:.1f}, {new_pos['y']*100:.1f}, {new_pos['z']*100:.1f})cm 도달. "
                f"{angle_info}. 남은 거리: {remaining_cm:.1f}cm. 다음 이동을 결정하거라.")

    except Exception as e:
        logger.error(f"robot_action error: {e}")
        return f"변환 및 계산 중 불충이 발생하였나이다: {str(e)}"