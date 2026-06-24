import torch
import logging
from ultralytics import YOLO
from shared.config import PathConfig

class YoloDetector:
    """
    [Layer 1: Perception] YOLOv11 모델을 활용한 고성능 객체 탐지 엔진입니다.
    
    입력받은 영상 프레임에서 학습된 사물들을 찾아내고, 
    각 사물의 이름, 픽셀 좌표(중심점), 그리고 경계 상자(BBox) 정보를 추출합니다.
    """
    def __init__(self, model_path: str = None, conf_threshold: float = 0.4):
        """
        AI 모델을 로드하고 연산 장치(GPU/CPU)를 설정합니다.
        
        Args:
            model_path: 사용할 YOLO 모델 파일 경로 (.pt)
            conf_threshold: 탐지 신뢰도 임계값 (기본 0.4)
        """
        # 1. 모델 경로 설정 (기본값: yolo11s_custom.pt - 커스텀 모델)
        if model_path is None:
            model_path = str(PathConfig.MODEL_DIR / "yolo11s_custom.pt")
            
        self.conf_threshold = conf_threshold
            
        # 2. 연산 장치 설정 (CUDA 가용 시 GPU 사용으로 가속)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        logging.info(f"[YoloDetector] AI 모델 로딩 시도: {model_path} (장치: {self.device})")
        
        try:
            # 3. 모델 로드 및 최적화
            self.model = YOLO(model_path).to(self.device)
            logging.info(f"[YoloDetector] yolo11s_custom 모델 로딩 성공 - 연산 가동 준비 완료")
        except Exception as e:
            logging.error(f"[YoloDetector] 모델 로딩 실패: {e}")
            raise RuntimeError(f"YOLO 모델을 로드할 수 없습니다: {model_path}")

    def detect(self, frame) -> list:
        """
        영상 프레임 내의 모든 물체를 탐지합니다.
        
        Args:
            frame: 분석할 RGB 영상 데이터 (Numpy Array)
        Returns:
            detections: 탐지된 물체 정보 리스트
                [{"name": "물체명", "pixel_center": (u, v), "bbox": (w, h)}, ...]
        """
        # 1. 추론 실행 (Inference: 학습된 메델을 가동하여 분석 결과를 추출하는 과정)
        # verbose=False로 설정하여 불필요한 로그 출력을 방지합니다.
        results = self.model(frame, verbose=False, conf=self.conf_threshold)
        
        detections = []
        
        # 2. 결과 파싱 (Parsing: 추출된 데이터를 시스템이 쓰기 좋게 가공하는 과정)
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                # 클래스 정보 추출
                cls_id = int(box.cls[0])
                name = self.model.names[cls_id]
                
                # 3. 픽셀 좌표 계산 (xywh 포맷: 중심 좌표와 크기를 나타내는 형식)
                # xywh[0, 1]은 중심점(center), [2, 3]은 폭과 높이(width, height)입니다.
                xywh = box.xywh[0].cpu().numpy()
                u, v = int(xywh[0]), int(xywh[1])
                w, h = int(xywh[2]), int(xywh[3])
                
                # BBox (Bounding Box: 물체를 감싸는 직사각형 경계 상자)
                
                detections.append({
                    "name": name,
                    "pixel_center": (u, v),
                    "bbox": (w, h)
                })
        
        return detections
