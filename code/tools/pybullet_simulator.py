import numpy as np
import cv2
from ultralytics import YOLO
from pybullet_server import PyBulletServer

class PyBulletSimulator:
    """
    YOLOv11 탐지 기능과 시뮬레이터 제어 기능을 결합한 통합 지휘관 클래스입니다.
    모든 거리와 좌표는 사용자 편의를 위해 cm 단위로 처리합니다.
    """
    def __init__(self, model_path="yolo11n.pt"):
        # 1. YOLOv11 모델을 불러와 지능을 장착합니다.
        self.model = YOLO(model_path)
        # 2. 연무장과 통신할 전령(Server)을 소환합니다.
        self.server = PyBulletServer()
        
        # 카메라 투영 설정 (server.py의 설정값과 일치해야 정확합니다)
        self.near = 0.01
        self.far = 10.0
        self.width = 600
        self.height = 480

    def calculate_real_coords(self, px, py, depth_val):
        """
        화면의 픽셀 좌표와 깊이 값을 실제 세계의 cm 좌표로 변환합니다.
        """
        # 깊이 값(0~1)을 실제 거리(m)로 변환하는 공식입니다.
        z_m = self.far * self.near / (self.far - (self.far - self.near) * depth_val)
        
        # 카메라 시야각을 고려하여 X, Y 좌표를 계산합니다.
        # 시뮬레이션 환경의 카메라 위치와 각도에 따라 보정이 필요할 수 있습니다.
        x_m = (px - self.width / 2) * (z_m / self.width)
        y_m = (py - self.height / 2) * (z_m / self.height)
        
        # m 단위를 cm 단위로 변환하여 반환합니다.
        return round(x_m * 100, 2), round(y_m * 100, 2), round(z_m * 100, 2)

    def scan_and_report(self):
        """
        현재 연무장을 살펴보고 탐지된 물체의 좌표를 cm 단위로 보고합니다.
        """
        # 전령을 통해 현재 화면과 깊이 지도를 가져옵니다.
        rgb_img = self.server.get_rgb_image()
        depth_map = self.server.get_depth_data()
        
        if rgb_img is None or depth_map is None:
            print("연무장에서 데이터를 가져오는 데 실패했습니다.")
            return []

        # YOLO 모델로 물체를 탐지합니다.
        results = self.model.predict(rgb_img, conf=0.5, verbose=False)
        found_objects = []

        for result in results:
            for box in result.boxes:
                # 탐지된 상자의 중앙 좌표를 구합니다.
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                
                # 중앙점의 깊이 값을 읽어 실제 cm 좌표로 변환합니다.
                d_val = depth_map[cy][cx]
                x_cm, y_cm, z_cm = self.calculate_real_coords(cx, cy, d_val)
                label = result.names[int(box.cls[0])]
                
                # 마마의 명대로 (x, y, z) 형식으로 보고합니다.
                print(f"({x_cm}, {y_cm}, {z_cm} cm) 위치에 {label} 이(가) 있사옵니다.")
                found_objects.append({"name": label, "pos": [x_cm, y_cm, z_cm]})
        
        return found_objects

    def move_to_target(self, target_name):
        """
        특정 물체의 위치를 파악하여 로봇팔을 해당 좌표로 이동시킵니다.
        """
        print(f"어명 받들겠나이다. {target_name}에게로 이동을 시작합니다.")
        
        # 주변을 먼저 스캔합니다.
        objects = self.scan_and_report()
        
        for obj in objects:
            if obj["name"] == target_name:
                # 서버는 m 단위를 사용하므로 다시 cm를 m로 변환하여 명령을 내립니다.
                target_m = [v / 100 for v in obj["pos"]]
                success = self.server.move_arm(target_m)
                
                if success:
                    print(f"{target_name}의 위치 {obj['pos']}cm 로 이동을 완료했습니다.")
                else:
                    print("로봇팔 이동에 실패했습니다. 서버 상태를 확인하십시오.")
                return
                
        print(f"연무장에서 {target_name}을(를) 찾을 수 없습니다.")