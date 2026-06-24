import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
from logger import get_logger
import os
import sys

# 파이불렛 서버 통신을 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_path = os.path.join(current_dir, 'tools')
if tools_path not in sys.path:
    sys.path.append(tools_path)

try:
    from pybullet_server import PyBulletServer
except ImportError:
    PyBulletServer = None

# 비전 시스템의 상태와 오류를 기록하기 위한 로거 설정
logger = get_logger('VISION')

class VisionSystem:
    def __init__(self, model_path=None, sim_mode=False):
        """
        비전 시스템 초기화.
        sim_mode가 True이면 파이불렛 시뮬레이션 모드로 동작하며,
        False이면 실제 리얼센스 카메라를 초기화함.
        """
        self.sim_mode = sim_mode
        self.model_path = model_path
        self.sim_server = None
        self.pipeline = None
        
        # 모델 경로 설정
        if self.model_path is None:
            base_directory = os.path.dirname(os.path.abspath(__file__))
            self.model_path = os.path.normpath(os.path.join(base_directory, "..", "data", "models", "yolo11n.pt"))
        
        self.model = YOLO(self.model_path)

        if self.sim_mode:
            # 파이불렛 시뮬레이션 모드 초기화
            if PyBulletServer:
                self.sim_server = PyBulletServer()
                logger.info("Vision system initialized in PyBullet simulation mode.")
            else:
                logger.error("PyBulletServer module not found.")
        else:
            # 리얼센스 카메라 모드 초기화 (기존 로직)
            try:
                self.pipeline = rs.pipeline()
                self.config = rs.config()
                self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 15)
                self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 15)
                self.profile = self.pipeline.start(self.config)
                self.align = rs.align(rs.stream.color)
                depth_sensor = self.profile.get_device().first_depth_sensor()
                self.depth_scale = depth_sensor.get_depth_scale()
                self.intrinsics = self.profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
                self.colorizer = rs.colorizer()
                logger.info(f"RealSense Vision system initialized. Depth scale: {self.depth_scale}")
            except Exception as error:
                logger.error(f"Camera initialization failed: {error}")
                raise

    def get_real_world_coordinates(self, pixel_x, pixel_y, depth_data):
        """
        픽셀 좌표를 실제 3D 공간 좌표(cm)로 변환함.
        리얼센스와 파이불렛 모드 각각에 맞는 계산법을 적용함.
        """
        if self.sim_mode:
            # 파이불렛 깊이 데이터(0~1)를 cm 단위로 변환 (카메라 파라미터 기반)
            near, far = 0.01, 10.0
            width, height = 600, 480
            depth_val = depth_data[pixel_y][pixel_x]
            
            # 파이불렛 투영 행렬 기반 거리 계산
            z_m = far * near / (far - (far - near) * depth_val)
            x_m = (pixel_x - width / 2) * (z_m / width)
            y_m = (pixel_y - height / 2) * (z_m / height)
            
            return round(x_m * 100, 2), round(y_m * 100, 2), round(z_m * 100, 2)
        else:
            # 리얼센스 픽셀 역투영 (기존 로직)
            dist = depth_data.get_distance(pixel_x, pixel_y)
            if dist > 0:
                point = rs.rs2_deproject_pixel_to_point(self.intrinsics, [pixel_x, pixel_y], dist)
                return round(point[0] * 100, 2), round(point[1] * 100, 2), round(point[2] * 100, 2)
        return 0.0, 0.0, 0.0

    def process_frame(self):
        """
        프레임을 가져와 물체를 탐지하고 실제 좌표(cm)를 산출함.
        모드에 따라 파이불렛 서버 또는 리얼센스 카메라에서 데이터를 수신함.
        """
        try:
            if self.sim_mode:
                # 파이불렛 서버에서 이미지 및 깊이 데이터 수신
                color_image = self.sim_server.get_rgb_image()
                depth_frame = self.sim_server.get_depth_data()
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame, alpha=255), cv2.COLORMAP_JET)
            else:
                # 실제 리얼센스 카메라에서 프레임 수신 및 정렬
                frames = self.pipeline.wait_for_frames(timeout_ms=5000)
                aligned_frames = self.align.process(frames)
                color_frame = aligned_frames.get_color_frame()
                depth_frame = aligned_frames.get_depth_frame() # rs.depth_frame 객체
                color_image = np.asanyarray(color_frame.get_data())
                depth_colormap = np.asanyarray(self.colorizer.colorize(depth_frame).get_data())

            if color_image is None or depth_frame is None:
                return None, None, "nothing", []

            # YOLO 탐지 수행
            results = self.model(color_image, verbose=False, conf=0.5)
            annotated_image = color_image.copy()
            detected_items = []
            coordinates = []

            if results:
                detection_result = results[0]
                annotated_image = detection_result.plot()
                
                for box in detection_result.boxes:
                    class_id = int(box.cls[0])
                    name = self.model.names[class_id]
                    confidence = float(box.conf[0])
                    box_coords = box.xyxy[0].cpu().numpy()
                    center_x = int((box_coords[0] + box_coords[2]) / 2)
                    center_y = int((box_coords[1] + box_coords[3]) / 2)
                    
                    # 좌표 변환 함수 호출 (cm 단위)
                    real_x, real_y, real_z = self.get_real_world_coordinates(center_x, center_y, depth_frame)
                    
                    detected_items.append(name)
                    coordinates.append({
                        'name': name, 'confidence': round(confidence, 2),
                        'x': real_x, 'y': real_y, 'z': real_z
                    })

            detection_text = ", ".join(set(detected_items)) if detected_items else "nothing"
            combined_display = np.hstack((annotated_image, depth_colormap))
            return combined_display, annotated_image, detection_text, coordinates
            
        except Exception as error:
            logger.error(f"Frame processing error: {error}")
            return None, None, "error", []

    def release(self):
        """리소스 해제 (리얼센스 전용)"""
        if self.pipeline and not self.sim_mode:
            self.pipeline.stop()