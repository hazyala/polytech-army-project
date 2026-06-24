import time
import threading
import numpy as np
import logging
try:
    import cv2
except ImportError:
    cv2 = None
    
from typing import Optional, Tuple

# 1. RealSense SDK(pyrealsense2) 라이브러리 가용성 체크
# 하드웨어가 없거나 라이브러리가 설치되지 않은 환경에서도 시스템이 정상 작동하도록 합니다.
RS_AVAILABLE = False
try:
    import pyrealsense2 as rs
    RS_AVAILABLE = True
except ImportError:
    RS_AVAILABLE = False

class RealSenseDriver:
    """
    [Layer 1: Sensor] RealSense 하드웨어 전용 저수준 드라이버입니다.
    
    이 클래슨는 Intel RealSense 카메라와 직접 통신하여 RGB 및 Depth 프레임을 획득합니다.
    AI 분석이나 고수준 인지 로직 없이 오직 '데이터 획득'과 '스레드 안전한 제공'에만 집중합니다.

    * RealSense SDK를 통해 다음과 같은 추가 확장 예정입니다.
    1. 기울기 및 각도 (Pitch, Roll): 
       - 가속도/자이로 데이터를 통해 지면 대비 기울기 획득 가능한 모델 사용중으로 구현 가능
       - [구현 예정] SDK의 Motion Stream(모션 스트림: 기울기나 가속도 등 움직임 정보)을 활성화하여 실시간 카메라 자세(Pose) 추출 로직 추가 가능.
    2. 정밀 정합 (Extrinsics: 카메라와 센서 간의 위치 및 각도 등 외부 정렬 상태):
       - 카메라 내부의 RGB 센서와 Depth 센서 간의 미세한 물리적 오프셋을 SDK에서 직접 가져와 보정 가능.
    3. 로봇 베이스 정합:
       - 카메라가 로봇 대비 설치된 각도는 로봇 관절 상태와 결합해야 하므로, 이는 VisionBridge 계층에서 관리함.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        패턴: Thread-safe Singleton (스레드 안전한 싱글톤: 여러 작업이 동시에 접근해도 단 하나의 인스턴스만 생성되도록 보장하는 방식)
        전체 시스템에서 단 하나의 RealSense 드라이버 인스턴스만 존재해야 하므로 싱글톤을 적용합니다.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(RealSenseDriver, cls).__new__(cls)
        return cls._instance

    def __init__(self, fps=15):
        """
        드라이버 파라미터 및 프레임 버퍼를 초기화합니다.
        """
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        # GlobalConfig FPS 우선 적용
        try:
            from shared.config import GlobalConfig
            self.fps = GlobalConfig.CAMERA_FPS
        except:
            self.fps = fps
        
        logging.info(f"[Sensor] RealSense FPS 설정: {self.fps}")
        
        # [메인 카메라] 기본 RealSense 카메라 (고정 설치)
        self.running = False
        self.thread = None
        self.pipeline = None
        self.profile = None # Added profile initialization
        self.config = None
        
        # [그리퍼 카메라] 엔드 이펙터 장착 카메라 (선택적)
        self.gripper_running = False
        self.gripper_thread = None
        self.gripper_pipeline = None
        self.gripper_profile = None # Added gripper_profile initialization
        self.gripper_config = None
        
        # [IMU 데이터] 가속도/자이로 센서 (선택적)
        # IMU 데이터 버퍼 (Main / Gripper 분리)
        self.imu_data = {
            "main": {"accel": None, "gyro": None},
            "gripper": {"accel": None, "gyro": None}
        }
        self.imu_lock = threading.Lock() # Moved to general locks
        
        # [카메라 내인자] 정밀 좌표 변환을 위한 SDK 값
        # Intrinsics Storage (API 호환성)
        self.intrinsics = None
        self.depth_scale = 0.001
        
        self.gripper_intrinsics = None
        self.gripper_depth_scale = 0.001
        
        # [프레임 버퍼] 메인 카메라
        self.latest_color = None
        self.latest_depth = None
        self.frame_lock = threading.Lock()
        
        # [프레임 버퍼] 그리퍼 카메라
        self.gripper_latest_color = None
        self.gripper_latest_depth = None
        self.gripper_frame_lock = threading.Lock()
        
        # [타임아웃 추적] 연속 타임아웃 카운터
        self.timeout_count_main = 0
        self.timeout_count_gripper = 0
        
        logging.info(f"[RealSenseDriver] 드라이버 초기화 완료 (SDK 가용: {RS_AVAILABLE})")
        self.initialized = True

    def restart(self):
        """드라이버를 재시작합니다 (Stop -> Start)."""
        logging.info("[Sensor] RealSense 드라이버 재시작 중...")
        self.stop()
        time.sleep(2.0) # 하드웨어 정리 대기
        self.start()

    def _reset_device(self):
        """[내부] 연결된 첫 번째 장치를 찾아 하드웨어 리셋을 수행합니다."""
        try:
            ctx = rs.context()
            devices = ctx.query_devices()
            for dev in devices:
                logging.info(f"[Sensor] 장치 리셋: {dev.get_info(rs.camera_info.name)}")
                dev.hardware_reset()
        except Exception as e:
            logging.warning(f"[Sensor] 장치 리셋 실패: {e}")

    def start(self):
        """
        카메라 스트리밍을 시작합니다.
        RGB, Depth, 그리고 IMU(Accel/Gyro) 스트림을 모두 활성화합니다.
        """
        if self.running: return
        if not RS_AVAILABLE:
            logging.warning("[RealSenseDriver] SDK가 설치되지 않아 더미 데이터만 반환합니다.")
            return

        # [Hardware Reset] 시작 전 장치 상태 초기화 (권장)
        # self._reset_device() # 너무 느릴 수 있으므로 필요시 주석 해제

        try:
            # 파이프라인 초기화 (한 번만 수행)
            if self.pipeline is None:
                self.pipeline = rs.pipeline()
                
            config = rs.config()
            
            # [기본] RGB/Depth 스트림 설정 (640x480 @ 15fps)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, self.fps)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, self.fps)
            
            # [IMU] 가속도 및 자이로스코프 활성화
            try:
                from shared.config import GlobalConfig
                if hasattr(GlobalConfig, 'REALSENSE_ENABLE_IMU') and GlobalConfig.REALSENSE_ENABLE_IMU:
                    config.enable_stream(rs.stream.accel)
                    config.enable_stream(rs.stream.gyro)
                    logging.info("[RealSenseDriver] IMU 스트림(Accel/Gyro) 활성화 요청")
            except ImportError:
                pass

            # 스트리밍 시작
            self.profile = self.pipeline.start(config)
            
            # [Intrinsics] 내인자 추출 (Depth 스트림 기준)
            # as_video_stream_profile()로 변환해야 intrinsics 접근 가능
            depth_stream = self.profile.get_stream(rs.stream.depth).as_video_stream_profile()
            intr = depth_stream.get_intrinsics()
            
            # [API 호환성] intrinsics 객체 자체를 저장 (VisionBase 등에서 속성 접근 필요)
            self.intrinsics = intr
            
            # [Depth Scale] 뎁스 스케일 추출 (mm -> m 변환 계수)
            depth_sensor = self.profile.get_device().first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()
            
            logging.info(f"[RealSenseDriver] 메인 카메라 시작됨 (FPS={self.fps}, Scale={self.depth_scale:.5f})")
            logging.info(f"[RealSenseDriver] 내인자: fx={self.intrinsics.fx:.1f}, fy={self.intrinsics.fy:.1f}, "
                         f"cx={self.intrinsics.ppx:.1f}, cy={self.intrinsics.ppy:.1f}")

            self.running = True
            
            # 캡처 스레드 시작
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
        except Exception as e:
            logging.error(f"[RealSenseDriver] 시작 실패: {e}")
            self.running = False
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except:
                    pass
                self.pipeline = None
            self.profile = None # Ensure profile is also reset

    def start_gripper_camera(self):
        """
        그리퍼 카메라 파이프라인을 구성하고 백그라운드 캡처 스레드를 시작합니다.
        메인 카메라와 독립적으로 동작합니다.
        """
        from shared.config import GlobalConfig
        
        if not GlobalConfig.REALSENSE_ENABLE_GRIPPER_CAM:
            logging.info("[Sensor] 그리퍼 카메라가 비활성화되어 있습니다.")
            return
            
        if not RS_AVAILABLE:
            logging.error("[Sensor] RealSense SDK를 찾을 수 없습니다.")
            return
            
        if self.gripper_running: return
        
        try:
            # 시리얼 번호 가져오기
            serial = getattr(GlobalConfig, 'REALSENSE_GRIPPER_SERIAL', None)
            
            # 그리퍼 카메라용 별도 파이프라인 생성
            self.gripper_pipeline = rs.pipeline()
            self.gripper_config = rs.config()
            
            # 그리퍼 카메라 시리얼 번호로 특정 카메라 지정
            if serial:
                self.gripper_config.enable_device(serial)
                logging.info(f"[Sensor] 그리퍼 카메라 시리얼 지정: {serial}")
            else:
                logging.warning("[Sensor] 그리퍼 카메라 시리얼이 지정되지 않았습니다. 임의의 장치가 연결될 수 있습니다.")
            
            self.gripper_config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, self.fps)
            self.gripper_config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, self.fps)
            
            # IMU 데이터 활성화
            if hasattr(GlobalConfig, 'REALSENSE_ENABLE_IMU') and GlobalConfig.REALSENSE_ENABLE_IMU:
                self.gripper_config.enable_stream(rs.stream.accel)
                self.gripper_config.enable_stream(rs.stream.gyro)
            
            self.gripper_pipeline.start(self.gripper_config)
            
            # Intrinsics 추출
            profile = self.gripper_pipeline.get_active_profile()
            color_stream = profile.get_stream(rs.stream.color).as_video_stream_profile()
            self.gripper_raw_intrinsics = color_stream.get_intrinsics()
            
            self.gripper_intrinsics = {
                "fx": self.gripper_raw_intrinsics.fx,
                "fy": self.gripper_raw_intrinsics.fy,
                "cx": self.gripper_raw_intrinsics.ppx,
                "cy": self.gripper_raw_intrinsics.ppy
            }
            
            self.gripper_running = True
            self.gripper_thread = threading.Thread(target=self._gripper_capture_loop, daemon=True)
            self.gripper_thread.start()
            logging.info(f"[Sensor] 그리퍼 카메라 시작 완료: {self.gripper_intrinsics}")
        except Exception as e:
            logging.error(f"[Sensor] 그리퍼 카메라 초기화 실패: {e}")
            self.gripper_pipeline = None
            self.gripper_running = False

    def stop(self):
        """
        모든 하드웨어 파이프라인을 안전하게 닫고 스레드를 종료합니다.
        """
        # 메인 카메라 종료
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                logging.warning(f"[Sensor] 메인 파이프라인 종료 중 예외 발생: {e}")
            self.pipeline = None
            
        # 그리퍼 카메라 종료
        self.gripper_running = False
        if self.gripper_thread:
            self.gripper_thread.join(timeout=2.0)
            
        if self.gripper_pipeline:
            try:
                self.gripper_pipeline.stop()
            except Exception as e:
                logging.warning(f"[Sensor] 그리퍼 파이프라인 종료 중 예외 발생: {e}")
            self.gripper_pipeline = None
            
        logging.info("[Sensor] RealSense 드라이버가 안전하게 중지되었습니다.")

    def _capture_loop(self):
        """
        [인터널] 메인 카메라로부터 지속적으로 프레임을 읽어와 버퍼를 갱신하는 루프입니다.
        """
        fail_count = 0
        
        # GlobalConfig에서 타임아웃 설정 읽기
        from shared.config import GlobalConfig
        timeout_ms = GlobalConfig.REALSENSE_FRAME_TIMEOUT_MS
        max_retries = GlobalConfig.REALSENSE_MAX_TIMEOUT_RETRIES
        
        while self.running:
            try:
                # [Stability] 설정 가능한 타임아웃 적용 (기본 3초)
                frames = self.pipeline.wait_for_frames(timeout_ms=timeout_ms)
                
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                
                if not depth_frame or not color_frame:
                    fail_count += 1
                    if fail_count % 10 == 0:
                        logging.warning("[RealSenseDriver] 빈 프레임 수신 중...")
                    continue
                
                fail_count = 0 # 성공 시 카운트 리셋
                self.timeout_count_main = 0  # 타임아웃 카운터도 리셋

                # SDK 데이터를 Numpy 배열로 변환
                color_image = np.asanyarray(color_frame.get_data())
                depth_image = np.asanyarray(depth_frame.get_data())

                # [Lock] 버퍼 업데이트 시 스레드 동기화(동시 접근 방지) 보장
                with self.frame_lock:
                    self.latest_color = color_image
                    self.latest_depth = depth_image
                    
                # IMU 데이터 획득 (같은 프레임셋에 포함되어 있을 수 있음)
                if GlobalConfig.REALSENSE_ENABLE_IMU:
                    self._update_imu_data(frames, target='main')
                    
            except RuntimeError as e:
                # "Frame didn't arrive within XXX" 등의 타임아웃 에러
                if "arrive" in str(e):
                    self.timeout_count_main += 1
                    if self.timeout_count_main <= 2:  # 처음 2번만 로그 출력
                        logging.warning(f"[RealSenseDriver] 메인 카메라 프레임 타임아웃 ({timeout_ms}ms) - 재시도 중... ({self.timeout_count_main}/{max_retries})")
                    
                    # 최대 재시도 횟수 초과 시 경고
                    if self.timeout_count_main >= max_retries:
                        logging.error(f"[RealSenseDriver] 메인 카메라 연속 타임아웃 {max_retries}회 초과 - 카메라 연결 상태를 확인하세요")
                        self.timeout_count_main = 0  # 카운터 리셋
                else:
                    logging.error(f"[RealSenseDriver] 런타임 오류: {e}")
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"[RealSenseDriver] 캡처 중 알 수 없는 오류: {e}")
                time.sleep(0.5) # 오류 발생 시 재시도 대기시간 연장

            # 과도한 CPU 사용 방지 (FPS 제어)
            time.sleep(0.5 / self.fps) # 조금 여유를 둠

    def _gripper_capture_loop(self):
        """
        [인터널] 그리퍼 카메라로부터 지속적으로 프레임을 읽어와 버퍼를 갱신하는 루프입니다.
        """
        fail_count = 0
        
        # GlobalConfig에서 타임아웃 설정 읽기
        from shared.config import GlobalConfig
        timeout_ms = GlobalConfig.REALSENSE_FRAME_TIMEOUT_MS
        max_retries = GlobalConfig.REALSENSE_MAX_TIMEOUT_RETRIES
        
        while self.gripper_running:
            try:
                # [Stability] 설정 가능한 타임아웃 적용
                frames = self.gripper_pipeline.wait_for_frames(timeout_ms=timeout_ms)
                
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                
                if not depth_frame or not color_frame:
                    continue

                color_image = np.asanyarray(color_frame.get_data())
                depth_image = np.asanyarray(depth_frame.get_data())

                with self.gripper_frame_lock:
                    self.gripper_latest_color = color_image
                    self.gripper_latest_depth = depth_image
                    
                # 성공 시 타임아웃 카운터 리셋
                self.timeout_count_gripper = 0
                    
                # IMU 데이터 획득 (같은 프레임셋에 포함되어 있을 수 있음)
                if GlobalConfig.REALSENSE_ENABLE_IMU:
                    self._update_imu_data(frames, target='gripper')
                    
            except RuntimeError as e:
                # 타임아웃 에러 처리
                if "arrive" in str(e):
                    self.timeout_count_gripper += 1
                    if self.timeout_count_gripper <= 2:
                        logging.debug(f"[RealSenseDriver] 그리퍼 카메라 프레임 타임아웃 ({timeout_ms}ms) - 재시도 중... ({self.timeout_count_gripper}/{max_retries})")
                    
                    if self.timeout_count_gripper >= max_retries:
                        logging.warning(f"[RealSenseDriver] 그리퍼 카메라 연속 타임아웃 {max_retries}회 초과 - 연결 확인 필요")
                        self.timeout_count_gripper = 0
                else:
                    logging.debug(f"[RealSenseDriver] 그리퍼 카메라 런타임 오류: {e}")
                time.sleep(0.1)
                    
            except Exception as e:
                # 그리퍼 카메라는 연결이 불안정할 수 있으므로 디버그 레벨로 로그
                logging.debug(f"[RealSenseDriver] 그리퍼 카메라 캡처 대기 중... ({e})")
                time.sleep(0.5)

            time.sleep(0.5 / self.fps)

    def _update_imu_data(self, frames, target='main'):
        """
        [인터널] 프레임셋에서 IMU 데이터(가속도/자이로)를 추출하여 업데이트합니다.
        
        Args:
            frames: RealSense 프레임셋
            target: 'main' 또는 'gripper' - 데이터를 저장할 타겟 카메라
        """
        try:
            # 가속도 데이터
            accel_frame = frames.first_or_default(rs.stream.accel)
            if accel_frame:
                accel_data = accel_frame.as_motion_frame().get_motion_data()
                with self.imu_lock:
                    self.imu_data[target]["accel"] = {
                        "x": accel_data.x,
                        "y": accel_data.y,
                        "z": accel_data.z
                    }
            
            # 자이로 데이터
            gyro_frame = frames.first_or_default(rs.stream.gyro)
            if gyro_frame:
                gyro_data = gyro_frame.as_motion_frame().get_motion_data()
                with self.imu_lock:
                    self.imu_data[target]["gyro"] = {
                        "x": gyro_data.x,
                        "y": gyro_data.y,
                        "z": gyro_data.z
                    }
        except Exception as e:
            logging.debug(f"[RealSenseDriver] IMU 데이터 추출 실패 (일부 모델 미지원): {e}")

    def get_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """현재 가장 최신의 메인 카메라 RGB 및 Depth 프레임을 반환합니다."""
        with self.frame_lock:
            return self.latest_color, self.latest_depth

    def get_gripper_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """현재 가장 최신의 그리퍼 카메라 RGB 및 Depth 프레임을 반환합니다."""
        with self.gripper_frame_lock:
            return self.gripper_latest_color, self.gripper_latest_depth

    def get_imu_data(self, target='main') -> dict:
        """
        현재 IMU 데이터(가속도/자이로)를 반환합니다.
        
        Args:
            target: 'main' 또는 'gripper' - 조회할 카메라 타겟
        
        Returns:
            dict: {"accel": {x, y, z}, "gyro": {x, y, z}} 형태의 IMU 데이터
        """
        with self.imu_lock:
            return self.imu_data.get(target, {"accel": None, "gyro": None}).copy()

    def get_intrinsics(self) -> dict:
        """SDK에서 읽어온 실제 카메라 내인자(Intrinsics: 렌즈 파라미터) 값을 딕셔너리로 반환합니다."""
        return self.intrinsics

    def get_raw_intrinsics(self):
        """메인 카메라 SDK의 로우 내인자(Raw Intrinsics)를 반환합니다."""
        return self.raw_intrinsics

    def get_gripper_intrinsics(self) -> dict:
        """그리퍼 카메라의 내인자를 딕셔너리로 반환합니다."""
        return self.gripper_intrinsics

    def get_gripper_raw_intrinsics(self):
        """그리퍼 카메라 SDK의 로우 내인자를 반환합니다."""
        return self.gripper_raw_intrinsics

    def generate_rgb_stream(self):
        """
        Web UI의 실시간 스트리밍을 위한 MJPEG 데이터 생성기입니다.
        """
        while True:
            color, _ = self.get_frames()
            if color is not None:
                # 성능 및 대역폭을 고려하여 60% 품질로 인코딩
                ret, buffer = cv2.imencode('.jpg', color, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1.0 / self.fps)

    def generate_gripper_stream(self):
        """
        그리퍼 카메라의 Web UI 실시간 스트리밍을 위한 MJPEG 데이터 생성기입니다.
        """
        while True:
            color, _ = self.get_gripper_frames()
            if color is not None:
                ret, buffer = cv2.imencode('.jpg', color, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1.0 / self.fps)

# 전역 인스턴스 노출 (싱글톤 정책 준수)
realsense_driver = RealSenseDriver()
