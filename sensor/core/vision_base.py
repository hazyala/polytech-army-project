from abc import ABC, abstractmethod
from typing import List, Optional
from shared.filters import KalmanFilter

class VisionBase(ABC):
    """
    [Layer 1: Sensor] 비전 시스템의 공통 인터페이스 및 베이스 클래스입니다.
    
    이 클래스는 모든 비전 구현체(RealSense, PyBullet 등)가 지켜야 할 표준 규격을 정의하며,
    2D 픽셀 좌표와 깊이(Depth) 정보를 3D 공간 좌표로 변환하는 핵심 로직을 포함합니다.
    """

    def __init__(self):
        """
        비전 시스템의 기본 파라미터와 좌표 정제용 필터를 초기화합니다.
        """
        # [특징 1] 카메라 내인자(Intrinsics: 렌즈 고유의 초점 거리나 중심점 등 카메라 내부 속성) 
        # 하부 구현체에서 실제 카메라 하드웨어에 맞는 값으로 갱신하여 사용합니다.
        self.fx, self.fy = 600.0, 600.0 # 초점 거리 (기본값)
        self.cx, self.cy = 320.0, 240.0 # 이미지 중심점 (기본값)
        
        # [특징 2] 떨림 방지의 내재화 (KalmanFilter: 데이터의 흔들림을 잡아주는 수학적 필터)
        # 센서 데이터의 노이즈를 제거하기 위해 X, Y, Z축별로 독립적인 칼만 필터를 생성합니다.
        # 어떤 카메라 구현체를 사용하더라도 이 베이스 클래스를 통해 부드러운 좌표를 얻을 수 있습니다.
        self.filter_x = KalmanFilter()
        self.filter_y = KalmanFilter()
        self.filter_z = KalmanFilter()

    def set_intrinsics(self, fx: float, fy: float, cx: float, cy: float):
        """
        카메라의 내인자(Intrinsics: 렌즈의 초점 거리 및 픽셀 중심점 등) 값을 설정합니다.
        구현체에서 하드웨어 정보를 읽어온 후 호출합니다.
        """
        self.fx, self.fy = fx, fy
        self.cx, self.cy = cx, cy

    def pixel_to_cm(self, u: float, v: float, depth_m: float) -> Optional[List[float]]:
        """
        [특징 3] 좌표 변환 알고리즘 (Simplified Pinhole: 바늘구멍 사진기 원리를 이용한 단순 좌표 변환)
        
        2D 영상의 픽셀 좌표(u, v)와 거리(depth)를 받아 실제 3D cm 좌표로 변환합니다.
        복잡한 행렬 연산 대신, 이미지의 해상도와 깊이 사이의 비례 관계를 이용한 직관적인 방식을 사용합니다.
        
        Args:
            u, v: 화면상의 2D 픽셀 좌표
            depth_m: 센서로부터 측정된 깊이 (미터 단위)
        Returns:
            [x, y, z]: 필터링된 로봇 기준 3D cm 좌표 리스트
        """
        if depth_m <= 0:
            return None

        # [좌표 변환 로직]
        # 1. 단위 변환: m -> cm (로봇 제어는 cm 단위를 기본으로 함)
        z_cm = depth_m * 100.0
        
        # 2. 비례식 기반 X, Y 좌표 추정 (Simplified Pinhole: 단순 바늘구멍 모델)
        # 원리: 실제_길이 / 실제_거리 = (픽셀_좌표 - 중심) / 초점_거리
        # 현재는 화면 폭(WIDTH) 대비 비례를 사용하는 V1.0 방식을 유지합니다.
        WIDTH, HEIGHT = 640, 480 # 표준 QVGA 해상도 기준
        
        x_cm = (u - self.cx) * (z_cm / self.fx)
        y_cm = (v - self.cy) * (z_cm / self.fy)

        # 3. 좌표 정제 (Post-processing)
        # 계산된 원본 좌표에 즉시 칼만 필터를 적용하여 센서 떨림(Flickering)을 제거합니다.
        filtered_x = self.filter_x.update(x_cm)
        filtered_y = self.filter_y.update(y_cm)
        filtered_z = self.filter_z.update(z_cm)
        
        return [filtered_x, filtered_y, filtered_z]

    @abstractmethod
    def get_frame(self):
        """
        [특징 4] 추상화 인터페이스를 통한 영상 획득 강제
        
        이 메서드는 하부 구현체(RealSenseVision, PybulletVision 등)에서 
        반드시 환경에 맞는 영상 및 깊이 획득 로직으로 구현해야 합니다.
        """
        pass

    def measure_focus_score(self, image) -> float:
        """
        [특징 5] 이미지 선명도(Focus Score) 측정
        
        Laplacian Variance 알고리즘을 사용하여 이미지의 에지가 얼마나 뚜렷한지 수치화합니다.
        점수가 높을수록 이미지가 선명하고(초점이 잘 맞음), 낮을수록 흐릿합니다(Blurry).
        
        Args:
            image: OpenCV 포맷의 이미지 (BGR)
        Returns:
            float: 선명도 점수 (Variance of Laplacian)
        """
        try:
            import cv2
            if image is None: return 0.0
            
            # 흑백 변환 후 라플라시안 필터 적용
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            score = cv2.Laplacian(gray, cv2.CV_64F).var()
            return float(score)
        except Exception:
            return 0.0