import logging
import threading
import time
import numpy as np
from shared.config import GlobalConfig, CameraConfig
from ..implementations import PybulletVision, RealSenseVision
from .yolo_detector import YoloDetector
from state.system_state import system_state

class VisionBridge:
    """
    [Layer 1: Perception Bridge] 하드웨어 드라이버와 AI 모델을 연결하는 핵심 중계 계층입니다.
    
    이 클래스는 영상 소스(Real/Sim)를 관리하고, YOLO가 찾은 2D 픽셀 좌표를 
    로봇이 실제 팔을 뻗을 수 있는 3D cm 좌표로 변환하는 '좌표 정제' 프로세스를 총괄합니다.
    """
    def __init__(self):
        """
        초기 설정에 따라 비전 소스를 선택하고 탐지용 엔진을 준비합니다.
        """
        self.sim_mode = GlobalConfig.SIM_MODE
        self.yolo = YoloDetector()

        # [특징: Multi-Camera Support]
        # 메인 카메라(월드)와 그리퍼 카메라(로컬) 드라이버를 모두 유지합니다.
        # 필요에 따라 활성화된 소스(self.current_driver)를 교체하며 사용합니다.
        self.drivers = {}
        
        if self.sim_mode:
            self._setup_virtual_source()
        else:
            self._setup_real_source()
            
        self.current_source_key = 'main' # 'main' or 'gripper'
        self.current_mode = "DEFAULT"    # "STEADYCAM", "EXPLORATION", "EXPLOITATION"

    def _setup_virtual_source(self):
        """시뮬레이션(PyBullet) 비전 소스를 구성합니다."""
        # Main Camera
        main_cam = PybulletVision()
        self.drivers['main'] = main_cam
        
        # Gripper Camera (PybulletVision 인스턴스 공유하되 별도 처리 가능하지만, 
        # 여기서는 논리적 분리를 위해 드라이버 맵에 등록)
        self.drivers['gripper'] = main_cam 
        
        self.offset = CameraConfig.SIM_OFFSET
        logging.info("[VisionBridge] 가상 비전(Simulation) 소스 연결됨 (Main + Gripper).")

    def _setup_real_source(self):
        """실물(RealSense) 비전 소스를 구성합니다."""
        real_vision = RealSenseVision()
        self.drivers['main']   = real_vision
        self.drivers['gripper'] = real_vision  # 동일 인스턴스 공유 (싱글톤 드라이버)

        self.offset = CameraConfig.REAL_OFFSET

        # [Calibration] MultiCameraCalibrator 로드
        # 캘리브레이션 파일이 있으면 자동으로 행렬을 복원합니다.
        try:
            from sensor.calibration_system import MultiCameraCalibrator
            self.multi_calibrator = MultiCameraCalibrator()
            status = self.multi_calibrator.get_status()
            logging.info(f"[VisionBridge] 캘리브레이션 상태: {status}")
        except Exception as e:
            logging.warning(f"[VisionBridge] MultiCameraCalibrator 로드 실패 (레거시 오프셋 사용): {e}")
            self.multi_calibrator = None

        logging.info("[VisionBridge] 실물 비전(RealSense) 소스 연결됨 (Main + Gripper).")

    def set_mode(self, mode: str):
        """
        비전 시스템의 운용 모드를 설정합니다.
        Args:
            mode: "STEADYCAM", "EXPLORATION", "EXPLOITATION"
        """
        self.current_mode = mode
        
        # 모드에 따른 카메라 자동 전환 로직
        if mode == "EXPLOITATION":
            # 정밀 조작 시 그리퍼 카메라 우선
            self.switch_source('gripper')
        else:
            # 탐색 및 일반 주행 시 메인 카메라 우선
            self.switch_source('main')
            
        logging.info(f"[VisionBridge] 비전 모드 변경: {mode} (Source: {self.current_source_key})")
        
        # 시스템 상태에도 반영
        system_state.camera_mode = mode

    def switch_source(self, source_key: str):
        """
        실시간으로 카메라 소스를 전환합니다.
        Args:
            source_key: 'main', 'gripper', 'realsense'
        """
        # 'realsense' 소스 요청 시 'main' 소스로 자동 매핑
        if source_key == 'realsense':
            source_key = 'main'
            logging.info("[VisionBridge] 'realsense' 소스 요청 → 'main' 소스로 매핑됨")
        
        if source_key not in self.drivers:
            logging.warning(f"[VisionBridge] 알 수 없는 소스: {source_key}")
            return

        # [버그 수정] 실물 모드에서도 그리퍼 전환 허용 (기존 코드가 sim_mode 조건 반전되어 있었음)
        if self.sim_mode and source_key == 'gripper':
            logging.warning("[VisionBridge] 그리퍼 카메라는 PyBullet 시뮬레이션에서만 별도 처리됩니다.")

        self.current_source_key = source_key
        logging.info(f"[VisionBridge] 카메라 소스 활성화: {source_key}")

    def change_environment(self, sim_mode: bool):
        """
        [Dynamic Mode Switch] 런타임에 시뮬레이션과 실물 모드를 동적으로 전환합니다.
        """
        if self.sim_mode == sim_mode:
            return
            
        logging.info(f"[VisionBridge] 환경 전환 요청됨. Sim Mode: {self.sim_mode} -> {sim_mode}")
        self.sim_mode = sim_mode
        self.drivers.clear()
        
        if self.sim_mode:
            self._setup_virtual_source()
        else:
            self._setup_real_source()

    def _fetch_packet(self):
        """현재 설정된 소스 타입에 따라 적절한 패킷을 가져옵니다."""
        driver = self.drivers.get('main') # 기본 드라이버 인스턴스
        
        if self.sim_mode and self.current_source_key == 'gripper':
            # PybulletVision의 capture_gripper 호출
            return driver.capture_gripper()
        else:
            return driver.get_synced_packet()

    def get_raw_frame(self):
        """
        VLM 분석 등을 위해 보정되지 않은 순수 원본 영상 프레임을 반환합니다.
        추가로 Focus Score(선명도)를 계산하여 SystemState에 업데이트합니다.
        """
        packet = self._fetch_packet()
        if not packet: return None
        
        color_frame = packet.get("color")
        
        # [Focus Score Update]
        if color_frame is not None:
             # 드라이버(VisionBase)에 구현된 선명도 측정 사용
             driver = self.drivers.get('main')
             score = driver.measure_focus_score(color_frame)
             system_state.focus_score = round(score, 2)
             
        return color_frame

    def get_gripper_frame(self):
        """
        [Helper] 그리퍼 카메라의 영상을 별도로 가져옵니다 (멀티뷰 디버깅용).
        """
        if 'gripper' not in self.drivers: return None, None
        
        driver = self.drivers['gripper']
        # Sim Mode: same instance, use capture_gripper
        if self.sim_mode:
            # 디버깅용 뎁스 데이터 포함
            packet = driver.capture_gripper(include_depth=True)
            if packet:
                return packet.get("color"), packet.get("depth")
            return None, None
        else:
            # Real Mode: if separate driver exists
            
            # TODO: 실물 그리퍼 카메라 드라이버 연동
            # 현재는 Main Driver가 Gripper 카메라이기도 한 경우(Singleton)를 고려해야 함
            # 하지만 VisionBridge 구조상 drivers['main']과 drivers['gripper']가 분리되어 있을 수 있음.
            
            # 임시: 그리퍼 드라이버가 있으면 가져오기
            packet = driver.get_gripper_synced_packet() # 그리퍼 전용 패킷 메서드 호출
            if packet:
                 return packet.get("color"), packet.get("depth")
            return None, None

    def get_refined_detections(self) -> list:
        """
        [Core Logic] 픽셀 좌표를 로봇 기준 3D cm 좌표로 정밀 변환합니다.
        
        흐름: 
        1. 동기화된 데이터(Color/Depth/Pose) 획득
        2. YOLO 2D 탐지 실행
        3. ROI 분석 및 적응형 깊이 추정 (Spherical Compensation)
        4. 카메라 오프셋 보정 및 로봇 베이스 좌표 산출
        """
        # 1. 동기화 패킷 획득 (현재 소스에 따라 변경)
        packet = self._fetch_packet()
        if not packet:
            # 패킷 없음 - 빈 결과와 None 프레임 반환
            return [], None, None

        color_frame = packet.get("color")
        depth_frame = packet.get("depth")
        captured_pose = packet.get("captured_pose", {})
        
        if color_frame is None or depth_frame is None:
            # 프레임 누락 - 빈 결과와 가용 프레임 반환
            return [], color_frame, None

        # 2. YOLO 2D 객체 탐지
        raw_detections = self.yolo.detect(color_frame)
        
        refined_list = []
        for det in raw_detections:
            u, v = det["pixel_center"]
            
            # 3. [ROI(Region of Interest: 이미지 내에서 분석하고자 하는 특정 관심 영역) 기반 고정밀 깊이 추출]
            # 단순히 한 점(u, v)의 깊이만 읽으면 노이즈에 취약합니다.
            # 물체 중심부의 영역(ROI)을 통계적으로 분석하여 대표 깊이를 산출합니다.
            
            # BBox(경계 상자)의 중앙 40% 영역만 추출 (배경 노이즈 배제)
            margin_w = int(det["bbox"][0] * 0.3)
            margin_h = int(det["bbox"][1] * 0.3)
            
            u_min = max(0, u - det["bbox"][0] // 2 + margin_w)
            u_max = min(depth_frame.shape[1], u + det["bbox"][0] // 2 - margin_w)
            v_min = max(0, v - det["bbox"][1] // 2 + margin_h)
            v_max = min(depth_frame.shape[0], v + det["bbox"][1] // 2 - margin_h)
            
            depth_roi = depth_frame[v_min:v_max, u_min:u_max]
            
            # 유효 범위(0.1m ~ 3.0m) 필터링
            valid_depths = depth_roi[(depth_roi > 0.1) & (depth_roi < 3.0)]
            
            if len(valid_depths) > 0:
                # [적응형 중심 추정 - Spherical Compensation(구면 보정: 렌즈 굴곡으로 인한 거리 오차를 바로잡는 것)]
                # 물체는 표면(Surface)만 찍히지만, 로봇은 중심(Center)을 잡아야 합니다.
                # 알고리즘: Median(중간값: 데이터의 한가운데 값) + Std(표준편차: 데이터가 퍼진 정도, 여기서는 물체의 곡률 반영)
                # 입체적인 물체일수록 Std가 크므로 더 깊은 곳(중심)을 바라보게 됩니다.
                median_d = float(np.median(valid_depths))
                std_d = float(np.std(valid_depths))
                depth_m = median_d + std_d
            else:
                # ROI 분석 불가 시 중앙점 값 사용 (Fallback: 대비책)
                depth_m = depth_frame[v, u] if v < depth_frame.shape[0] and u < depth_frame.shape[1] else 0
            
            if depth_m <= 0.1: continue

            # 4. 픽셀-to-3D 변환 (cm 단위)
            coords_cm = None 
            log_type = "Unknown"
            
            # [Dynamic Kinematics] 그리퍼 카메라(Local) 처리
            if self.sim_mode and self.current_source_key == 'gripper':
                # 4-1. 카메라 기준 로컬 좌표 획득
                coords_local = self.drivers['gripper'].pixel_to_local_cm(u, v, depth_m)
                
                if coords_local:
                    # 4-2. 로봇 데이터에서 관절값(Wrist Roll)과 EE 포즈 획득
                    # captured_pose는 EE(End Effector)의 월드 좌표 + 오리엔테이션
                    ee_pos = captured_pose.get('pos', [0,0,0]) # [x, y, z]
                    ee_orn = captured_pose.get('orn', [0,0,0,1]) # [x, y, z, w]
                    
                    # 4-3. [Dynamic Kinematics] 좌표계 변환: View -> EE Local -> World
                    # pybullet_sim.py 분석 결과 오프셋은 0이며, 회전 변환만 수행하면 됨
                    from sensor.projection import pybullet_projection
                    
                    coords_cm = pybullet_projection.project_gripper_camera_to_world(coords_local, ee_pos, ee_orn)
                    log_type = "그리퍼(Dynamic 6-DOF 보정)"
                    
            # [Standard] 메인 카메라/월드 카메라 처리
            else:
                coords_cm = self.drivers['main'].pixel_to_cm(u, v, depth_m)
            
            if coords_cm:
                # 5. [좌표계 통합] 카메라 좌표 -> 로봇 베이스 좌표
                if self.current_source_key == 'gripper' and self.sim_mode:
                    # 시뮬레이션 그리퍼: 이미 위에서 World 좌표로 변환됨
                    rx, ry, rz = coords_cm
                elif type(self.drivers['main']).__name__ == "PybulletVision":
                    # PyBullet 메인 카메라: GT 보정
                    rx, ry, rz = coords_cm
                    log_type = "월드(GT보정)"
                else:
                    # [실물 모드] 캘리브레이션 행렬 우선 적용
                    calibrator = getattr(self, 'multi_calibrator', None)
                    if calibrator and self.current_source_key == 'gripper':
                        # 그리퍼 카메라 전용 캘리브레이션 행렬
                        if calibrator.gripper_calibrator.transform_matrix is not None:
                            rx, ry, rz = calibrator.gripper_to_robot(coords_cm[0], coords_cm[1], coords_cm[2])
                            log_type = "그리퍼(캘리브레이션행렬)"
                        else:
                            # Fallback: 레거시 오프셋
                            rx = coords_cm[0] + self.offset["x"]
                            ry = coords_cm[1] + self.offset["y"]
                            rz = coords_cm[2] + self.offset["z"]
                            log_type = "그리퍼(레거시오프셋)"
                    elif calibrator and calibrator.world_calibrator.transform_matrix is not None:
                        # 메인 카메라 전용 캘리브레이션 행렬
                        rx, ry, rz = calibrator.world_to_robot(coords_cm[0], coords_cm[1], coords_cm[2])
                        log_type = "월드(캘리브레이션행렬)"
                    else:
                        # Fallback: 레거시 오프셋 (캘리브레이션 미완료 시)
                        rx = coords_cm[0] + self.offset["x"]
                        ry = coords_cm[1] + self.offset["y"]
                        rz = coords_cm[2] + self.offset["z"]
                        log_type = "월드(레거시오프셋)"
                
                logging.debug(f"[VisionBridge] 탐지 완료: '{det['name']}' -> {log_type}=({rx:.2f}, {ry:.2f}, {rz:.2f})cm")

                refined_list.append({
                    "name": det["name"],
                    "position": {"x": round(rx, 2), "y": round(ry, 2), "z": round(rz, 2)},
                    "pixel_center": det["pixel_center"],
                    "bbox": det["bbox"],
                    "sync_pose": captured_pose
                })
                
        # ──────────────────────────────────────────────
        # [색상 마커 탐지] 실물 모드에서 HSV 기반 빨간 테이프 마커 검출
        # YOLO 탐지와 병행하여, 마커가 보이면 'red_marker' 타겟으로 추가합니다.
        # 이를 통해 비주얼 서보잉이 색상 마커를 추적할 수 있습니다.
        # ──────────────────────────────────────────────
        if not self.sim_mode:
            try:
                from sensor.calibration_system import RedTapeDetector
                
                # RedTapeDetector 인스턴스를 캐싱하여 매 호출마다 재생성하지 않음
                if not hasattr(self, '_marker_detector'):
                    self._marker_detector = RedTapeDetector()
                    logging.info("[VisionBridge] 🔴 색상 마커 탐지기(RedTapeDetector) 초기화됨")
                
                marker_result = self._marker_detector.detect(color_frame, depth_frame)
                
                if marker_result:
                    u_m, v_m, depth_m_marker = marker_result
                    
                    # 깊이값 유효성 검증
                    if depth_m_marker > 0.05:
                        # 픽셀 → 3D 카메라 좌표 변환 (cm)
                        coords_cm = self.drivers['main'].pixel_to_cm(u_m, v_m, depth_m_marker)
                        
                        if coords_cm:
                            # 카메라 좌표 → 로봇 베이스 좌표 변환 (기존 파이프라인 재활용)
                            calibrator = getattr(self, 'multi_calibrator', None)
                            if calibrator and calibrator.world_calibrator.transform_matrix is not None:
                                rx, ry, rz = calibrator.world_to_robot(
                                    coords_cm[0], coords_cm[1], coords_cm[2]
                                )
                                marker_log = "색상마커(캘리브레이션행렬)"
                            else:
                                # Fallback: 레거시 오프셋
                                rx = coords_cm[0] + self.offset["x"]
                                ry = coords_cm[1] + self.offset["y"]
                                rz = coords_cm[2] + self.offset["z"]
                                marker_log = "색상마커(레거시오프셋)"
                            
                            logging.debug(
                                f"[VisionBridge] 🔴 마커 탐지: {marker_log}"
                                f"=({rx:.2f}, {ry:.2f}, {rz:.2f})cm"
                            )
                            
                            refined_list.append({
                                "name": "red_marker",
                                "position": {
                                    "x": round(rx, 2), 
                                    "y": round(ry, 2), 
                                    "z": round(rz, 2)
                                },
                                "pixel_center": (u_m, v_m),
                                "bbox": (30, 30),  # 마커 고정 크기
                                "sync_pose": captured_pose
                            })
                            
            except ImportError:
                # calibration_system 모듈이 없으면 색상 마커 탐지를 건너뜀
                pass
            except Exception as e:
                logging.warning(f"[VisionBridge] 색상 마커 탐지 오류 (무시): {e}")
        
        # 항상 튜플 (list, color_frame, depth_frame)을 반환하도록 보장
        return refined_list, color_frame, depth_frame

    # NOTE: 백그라운드 업데이트 루프는 PerceptionManager에서 통합 관리하므로
    # 이 클래스 내부의 중복된 루프 로직은 제거되었습니다.

