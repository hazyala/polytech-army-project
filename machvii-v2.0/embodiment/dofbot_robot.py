# embodiment/dofbot_robot.py

import logging
import socketio
import threading
import time
from typing import Tuple, Optional, List
from .robot_base import RobotBase
from shared.config import GlobalConfig

class DofbotRobot(RobotBase):
    """
    [Layer 6: Embodiment] DOFBOT 실물 로봇 클라이언트
    
    Flask-SocketIO 기반 DOFBOT 서버와 통신합니다.
    
    [서버 프로토콜 (참고: DOFBOT_ROBOT_ARM-main/main.py)]
    ── 수신 이벤트 (클라이언트 → 서버) ──
      - set_pos   : XYZ 좌표 이동 {'pos': [x, y, z]} (미터 단위)
      - set_gripper: 그리퍼 각도  {'gripper': 0~180}
      - set_torque : 토크 ON/OFF {'torque': 0 또는 1}
    
    ── 브로드캐스트 (서버 → 클라이언트, 50ms 주기) ──
      - robot_state: {'ee': {'x','y','z'}, 'joints': [5개 각도(도)]}
    
    [주의]
      - set_joints, set_force는 서버에 핸들러가 없으므로 set_pos로 대체합니다.
      - 위치 입력은 cm, 서버 통신은 m 단위입니다. 반드시 변환이 필요합니다.
    """
    
    def __init__(self):
        # RobotBase 초기화 (current_state 딕셔너리 세팅)
        super().__init__()
        
        self.sio = socketio.Client()
        self.server_url = GlobalConfig.DOFBOT_SERVER_URL
        self.connected = False
        
        # 서버로부터 실시간 수신되는 최신 상태 저장소
        self.latest_state = {}
        self.state_lock = threading.Lock()
        
        # 이벤트 핸들러 등록
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('robot_state', self._on_robot_state)
        
        # 초기화 시 1회 연결 시도
        self.connect()
        
    def connect(self):
        """DOFBOT 서버에 SocketIO 연결을 시도합니다."""
        try:
            logging.info(f"[DofbotRobot] 연결 시도: {self.server_url}")
            self.sio.connect(
                self.server_url, 
                transports=['websocket', 'polling'], 
                wait_timeout=5
            )
            self.connected = True
        except Exception as e:
            logging.error(f"[DofbotRobot] 연결 실패: {e}")
            self.connected = False

    def disconnect(self):
        """SocketIO 연결을 종료합니다."""
        if self.connected:
            self.sio.disconnect()
            
    # ──────────────────────────────────────────────
    # SocketIO 이벤트 핸들러
    # ──────────────────────────────────────────────
            
    def _on_connect(self):
        """서버 연결 성공 시 호출됩니다."""
        self.connected = True
        logging.info("[DofbotRobot] ✅ 연결됨!")
        
    def _on_disconnect(self):
        """서버 연결 끊김 시 호출됩니다."""
        self.connected = False
        logging.info("[DofbotRobot] ❌ 연결 끊김!")
        
    def _on_robot_state(self, data):
        """
        서버로부터 50ms 주기로 브로드캐스트되는 로봇 상태를 수신합니다.
        
        data 구조 (참고 서버 기준):
        {
            'ee': {'x': float, 'y': float, 'z': float},  # EE 위치 (미터)
            'joints': [float, float, float, float, float]  # 관절 각도 (도)
        }
        """
        with self.state_lock:
            self.latest_state = data
    
    # ──────────────────────────────────────────────
    # 이동 제어 (RobotBase 인터페이스 구현)
    # ──────────────────────────────────────────────
            
    def move_to(self, x: float, y: float, z: float, 
                speed: float = 1.0, wait: bool = True) -> bool:
        """
        XYZ 좌표로 로봇 끝단을 이동시킵니다.
        
        서버의 set_pos 이벤트를 사용합니다.
        IKPy 역기구학 계산은 서버 측(robot_thread.py)에서 수행됩니다.
        
        Args:
            x, y, z: 목표 좌표 (단위: cm)
            speed: 이동 속도 (현재 서버 미지원, 예약됨)
            wait: True이면 이동 완료까지 대기
        Returns:
            bool: 명령 전송 성공 여부
        """
        if not self.connected:
            logging.warning("[DofbotRobot] 로봇 미연결 상태에서 이동 시도")
            
        try:
            # cm → m 변환 (서버는 미터 단위)
            pos_m = [x / 100.0, y / 100.0, z / 100.0]
            
            logging.info(f"[DofbotRobot] 이동 명령: ({x:.1f}, {y:.1f}, {z:.1f})cm → {pos_m}m")
            self.sio.emit('set_pos', {'pos': pos_m})
            
            if wait:
                # 서버에 is_moving 상태가 없으므로 고정 대기
                # TODO: 서버가 이동 완료 이벤트를 지원하면 비동기 대기로 전환
                time.sleep(1.0)
            return True
        except Exception as e:
            logging.error(f"[DofbotRobot] 이동 에러: {e}")
            return False

    def move_to_xyz(self, x: float, y: float, z: float, speed: int = 50) -> bool:
        """
        RobotBase 추상 메서드 구현.
        move_to()를 호출하여 XYZ 좌표로 이동합니다.
        """
        return self.move_to(x, y, z, speed=speed, wait=True)

    def set_joints(self, angles: List[float], speed: int = 50) -> bool:
        """
        관절 각도를 직접 제어합니다.
        
        [주의] 참고 서버(DOFBOT_ROBOT_ARM-main)에는 set_joints 핸들러가 없습니다.
        이벤트를 전송하되, 서버가 핸들러를 등록하지 않았으면 무시됩니다.
        서버 확장 시 해당 핸들러를 추가하면 즉시 동작합니다.
        
        Args:
            angles: 5개 관절의 목표 각도 리스트 (단위: 도)
            speed: 이동 속도 (0 ~ 100, 서버 확장 시 사용)
        """
        try:
            logging.info(f"[DofbotRobot] 관절 제어: {angles}")
            # 서버에 set_joints 핸들러가 있으면 동작, 없으면 무시됨 (Graceful)
            self.sio.emit('set_joints', {'joints': angles, 'speed': speed})
            time.sleep(1.5)  # 관절 이동 대기
            return True
        except Exception as e:
            logging.error(f"[DofbotRobot] 관절 제어 에러: {e}")
            return False

    # ──────────────────────────────────────────────
    # 그리퍼 제어
    # ──────────────────────────────────────────────

    def set_gripper(self, open_percent: float) -> bool:
        """
        그리퍼의 개폐를 제어합니다.
        
        0%는 완전히 닫힘(10도), 100%는 완전히 열림(170도)에 매핑됩니다.
        서버의 set_gripper 이벤트를 사용합니다.
        
        Args:
            open_percent: 그리퍼 개방 정도 (0 ~ 100)
        """
        try:
            # percent → 서보 각도 변환 (10 ~ 170 범위)
            angle = 10 + (open_percent / 100.0) * 160
            self.sio.emit('set_gripper', {'gripper': int(angle)})
            return True
        except Exception as e:
            logging.error(f"[DofbotRobot] 그리퍼 에러: {e}")
            return False

    def move_gripper(self, open_percent: float) -> bool:
        """RobotBase 추상 메서드 구현. set_gripper() 래퍼."""
        return self.set_gripper(open_percent)

    # ──────────────────────────────────────────────
    # 토크 및 힘 제어
    # ──────────────────────────────────────────────

    def set_torque(self, enabled: bool) -> bool:
        """
        서보 토크를 ON/OFF 합니다.
        
        서버의 set_torque 이벤트를 사용합니다 (참고 서버 지원됨).
        OFF 시 로봇이 힘을 풀고 자유 상태가 됩니다 (수동 조작 가능).
        
        Args:
            enabled: True=토크 ON, False=토크 OFF
        """
        try:
            torque_val = 1 if enabled else 0
            logging.info(f"[DofbotRobot] 토크 {'ON' if enabled else 'OFF'}")
            self.sio.emit('set_torque', {'torque': torque_val})
            return True
        except Exception as e:
            logging.error(f"[DofbotRobot] 토크 제어 에러: {e}")
            return False

    def set_force(self, force: float) -> bool:
        """
        힘 레벨을 설정합니다.
        
        [주의] 참고 서버에 set_force 핸들러가 없으므로,
        force=0이면 set_torque(False)로 대체합니다.
        
        Args:
            force: 힘 레벨 (0 ~ 500)
        """
        if force <= 0:
            return self.set_torque(False)
        else:
            return self.set_torque(True)

    # ──────────────────────────────────────────────
    # 상태 조회
    # ──────────────────────────────────────────────

    def get_current_pose(self) -> dict:
        """
        로봇의 현재 상태를 반환합니다.
        서버로부터 50ms 주기로 브로드캐스트되는 데이터를 기반으로 구성합니다.
        
        Returns:
            dict: {
                'position': {'x': float, 'y': float, 'z': float},  # cm 단위
                'joints': [float x 5],  # 도 단위
                'is_moving': bool
            }
        """
        with self.state_lock:
            if not self.latest_state:
                # 서버로부터 아직 데이터를 받지 못한 경우 기본값 반환
                return {
                    "position": {"x": 0, "y": 0, "z": 0},
                    "joints": [0] * 5,
                    # TODO: 서버가 gripper 상태를 브로드캐스트하면 활성화
                    # "gripper": 0,
                    "is_moving": False
                }
            
            # EE 위치: m → cm 변환
            ee = self.latest_state.get('ee', {})
            position = {
                "x": ee.get('x', 0) * 100.0,
                "y": ee.get('y', 0) * 100.0,
                "z": ee.get('z', 0) * 100.0
            }
            
            # 관절 각도 (도 단위, 서버에서 직접 수신)
            joints = self.latest_state.get('joints', [0] * 5)
            
            # TODO: 서버 확장 후 아래 데이터 활성화
            # gripper = self.latest_state.get('gripper', 0)
            # orientation = self.latest_state.get('orientation', {"roll":0, "pitch":0, "yaw":0})
            # joint_velocities = self.latest_state.get('joint_velocities', [0]*5)
            
            # 이동 상태: 서버가 보내면 사용, 아니면 False
            is_moving = self.latest_state.get('is_moving', False)
            
            return {
                "position": position,
                "joints": joints,
                # TODO: 서버 확장 후 활성화
                # "gripper": gripper,
                # "orientation": orientation,
                # "joint_velocities": joint_velocities,
                "is_moving": is_moving
            }

    def get_current_position(self) -> Optional[Tuple[float, float, float]]:
        """EE 위치만 튜플로 반환합니다 (cm 단위)."""
        p = self.get_current_pose()["position"]
        return (p["x"], p["y"], p["z"])

    # ──────────────────────────────────────────────
    # 안전 제어
    # ──────────────────────────────────────────────

    def emergency_stop(self):
        """
        긴급 정지: 토크를 OFF하여 로봇이 힘을 풀도록 합니다.
        
        [안전 메커니즘]
        실물 로봇에서는 토크를 끄면 로봇이 자유 상태가 되어
        중력에 의해 내려앉습니다. 이것이 가장 안전한 정지 방법입니다.
        """
        logging.warning("[DofbotRobot] 🛑 긴급 정지: 토크 OFF!")
        self.set_torque(False)
