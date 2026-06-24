import threading
import time
import logging
import base64
import cv2
from .vision_bridge import VisionBridge
from state.system_state import system_state
from shared.state_broadcaster import broadcaster
from shared.config import GlobalConfig


class PerceptionManager:
    """
    [Layer 1: Sensor Management] 시각 인지 시스템의 최종 관리 클래스입니다.
    
    주기적으로 비전 데이터를 수집(Detection, Raw Frame 등)하여 전역 상태(Layer 2: State)를 업데이트하고,
    시스템의 다른 레이어들이 최신 비전 정보를 실시간으로 구독할 수 있도록 전파(Broadcast)합니다.

    [최적화 설계]
    - 탐지 루프(Detection Loop): 10Hz (0.1초) — 탐지/상태 갱신에 집중
    - 인코딩 루프(Encode Loop): 5Hz (0.2초) — Base64 인코딩 전용, CPU 부하 50% 감소
    - [Bug 3 완화] sim_client 임포트는 GlobalConfig.SIM_MODE 블록 내 지역 임포트 유지
      → perception_manager ↔ sim_client 간 모듈 레벨 순환 참조 차단
    """
    def __init__(self, detect_interval: float = 0.1, encode_interval: float = 0.2):
        """
        Args:
            detect_interval: 탐지 루프 주기 (기본 0.1초 = 10Hz)
            encode_interval: 인코딩 루프 주기 (기본 0.2초 = 5Hz) — CPU 부하 완화
        """
        self.bridge = VisionBridge()
        self.detect_interval = detect_interval
        self.encode_interval = encode_interval
        self.running = False

        # 탐지 루프 스레드
        self.detect_thread = None
        # [Fix - Bug 4] 인코딩 전용 스레드 분리 (Base64 인코딩 병목 해결)
        self.encode_thread = None

        # 탐지 루프 → 인코딩 루프 간 최신 프레임 공유 버퍼
        self._frame_lock = threading.Lock()
        self._latest_main_frame = None
        self._latest_main_depth = None
        self._latest_gripper_frame = None
        self._latest_gripper_depth = None

    def start(self):
        """백그라운드 루프(탐지 + 인코딩)를 시작합니다."""
        if self.running:
            return
        self.running = True

        # 탐지 루프 시작 (10Hz)
        self.detect_thread = threading.Thread(
            target=self._detect_loop, daemon=True, name="PerceptionDetect"
        )
        self.detect_thread.start()

        # [Fix - Bug 4] 인코딩 루프 시작 (5Hz) — 탐지 루프와 완전 분리
        self.encode_thread = threading.Thread(
            target=self._encode_loop, daemon=True, name="PerceptionEncode"
        )
        self.encode_thread.start()

        logging.info("[PerceptionManager] 비전 인지 루프 가동 시작 (탐지 10Hz / 인코딩 5Hz).")

    def stop(self):
        """루프를 안전하게 종료합니다."""
        self.running = False
        if self.detect_thread:
            self.detect_thread.join(timeout=2.0)
        if self.encode_thread:
            self.encode_thread.join(timeout=2.0)
        logging.info("[PerceptionManager] 비전 인지 루프 정지.")

    # ──────────────────────────────────────────────
    # 탐지 루프 (10Hz): 탐지 + 로봇 상태 동기화
    # ──────────────────────────────────────────────
    def _detect_loop(self):
        """
        [Main Loop] 10Hz로 실행되는 객체 탐지 및 상태 갱신 루프.
        Base64 인코딩은 수행하지 않으며, 최신 프레임을 공유 버퍼에만 기록합니다.
        """
        while self.running:
            loop_start_time = time.time()
            try:
                # 1. 시각 탐지 및 3D 좌표 산출 (Main Camera 기준)
                detections, main_frame, main_depth = self.bridge.get_refined_detections()

                # 2. 전역 상태 업데이트
                new_perception = {
                    "detected_objects": detections,
                    "detection_count": len(detections),
                    "timestamp": time.time(),
                    "sensor_mode": "Sim" if GlobalConfig.SIM_MODE else "Real"
                }
                system_state.perception_data = new_perception

                # 3. 그리퍼 카메라 프레임 획득
                gripper_frame, gripper_depth = self.bridge.get_gripper_frame()

                # 4. [Fix - Bug 4] 인코딩 루프가 읽을 공유 버퍼에 최신 프레임 저장 (lock 보호)
                with self._frame_lock:
                    self._latest_main_frame = main_frame
                    self._latest_main_depth = main_depth
                    self._latest_gripper_frame = gripper_frame
                    self._latest_gripper_depth = gripper_depth

                # 5. [Bug 3 완화] SIM_MODE 블록 내 지역 임포트 유지
                #    → perception_manager ↔ sim_client 모듈 레벨 순환 참조 원천 차단
                if GlobalConfig.SIM_MODE:
                    from interface.backend.sim_client import pybullet_client
                    with pybullet_client.lock:
                        robot_info = pybullet_client.latest_state.get('robot', {})

                    system_state.robot.gripper_state = robot_info.get('gripper', 0.0)

                    current_status = robot_info.get('status', 'IDLE')
                    existing_status = system_state.robot.arm_status
                    if existing_status in ["VISUAL_SERVO", "GRASP", "SEARCH", "SUCCESS", "FAIL"]:
                        if current_status == "STUCK":
                            system_state.robot.arm_status = "STUCK"
                    else:
                        system_state.robot.arm_status = current_status

                    if current_status == "STUCK":
                        system_state.robot.is_unsafe = True
                        logging.critical("[Control Tower] 🚨 로봇 끼임(STUCK) 감지! 안전 모드 발동됨.")
                    else:
                        system_state.robot.is_unsafe = False

                # 6. 상태 전파
                broadcaster.publish("perception", new_perception)

            except Exception as e:
                logging.error(f"[PerceptionManager] 탐지 루프 오류: {e}")

            elapsed = time.time() - loop_start_time
            sleep_time = max(0, self.detect_interval - elapsed)
            time.sleep(sleep_time)

    # ──────────────────────────────────────────────
    # 인코딩 루프 (5Hz): Base64 인코딩 전용, CPU 부하 최소화
    # ──────────────────────────────────────────────
    def _encode_loop(self):
        """
        [Fix - Bug 4] 5Hz 인코딩 전용 루프.
        탐지 루프와 완전히 분리하여 UI 스트리밍용 Base64 인코딩 부하를 독립 처리합니다.
        탐지 주기(0.1s)보다 느린 0.2s 주기로 실행하여 CPU 부하를 절반으로 감소시킵니다.
        """
        while self.running:
            loop_start_time = time.time()
            try:
                # 공유 버퍼에서 최신 프레임 복사 (lock 최소화)
                with self._frame_lock:
                    main_frame = self._latest_main_frame
                    main_depth = self._latest_main_depth
                    gripper_frame = self._latest_gripper_frame
                    gripper_depth = self._latest_gripper_depth

                # ── 메인 컬러 프레임 인코딩 ──
                if main_frame is not None:
                    ret, buffer = cv2.imencode(
                        '.jpg', main_frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
                    )
                    if ret:
                        system_state.last_frame_base64 = base64.b64encode(buffer).decode('utf-8')

                # ── 메인 뎁스 프레임 인코딩 ──
                if main_depth is not None:
                    depth_vis = cv2.normalize(main_depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                    depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)
                    ret, buffer_d = cv2.imencode(
                        '.jpg', depth_vis, [cv2.IMWRITE_JPEG_QUALITY, 50]
                    )
                    if ret:
                        system_state.last_depth_base64 = base64.b64encode(buffer_d).decode('utf-8')

                # ── 그리퍼 컬러 프레임 인코딩 ──
                if gripper_frame is not None:
                    ret, buffer_ee = cv2.imencode(
                        '.jpg', gripper_frame, [cv2.IMWRITE_JPEG_QUALITY, 70]
                    )
                    if ret:
                        system_state.last_ee_frame_base64 = base64.b64encode(buffer_ee).decode('utf-8')

                # ── 그리퍼 뎁스 프레임 인코딩 ──
                if gripper_depth is not None:
                    depth_ee_vis = cv2.normalize(gripper_depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                    depth_ee_vis = cv2.applyColorMap(depth_ee_vis, cv2.COLORMAP_JET)
                    ret, buffer_ee_d = cv2.imencode(
                        '.jpg', depth_ee_vis, [cv2.IMWRITE_JPEG_QUALITY, 50]
                    )
                    if ret:
                        system_state.last_ee_depth_base64 = base64.b64encode(buffer_ee_d).decode('utf-8')

            except Exception as e:
                logging.error(f"[PerceptionManager] 인코딩 루프 오류: {e}")

            elapsed = time.time() - loop_start_time
            sleep_time = max(0, self.encode_interval - elapsed)
            time.sleep(sleep_time)


# 전역 싱글톤 인스턴스 노출
# 시스템 어디서든 perception_manager를 통해 비전 루프를 제어할 수 있습니다.
perception_manager = PerceptionManager()
