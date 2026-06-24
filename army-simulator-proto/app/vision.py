# app/vision.py
import cv2
import numpy as np
from ultralytics import YOLO

class VisionSystem:
    """
    YOLO 모델을 관리하고 이미지를 분석하는 클래스입니다.
    """
    def __init__(self, model_path='yolov8n.pt'):
        # 모델 로드 (에러 방지 처리 포함)
        try:
            self.model = YOLO(model_path)
            print(f"✅ VisionSystem 모델 로드 성공: {model_path}")
        except Exception as e:
            print(f"⚠️ 모델 로드 실패, 기본 모델로 전환: {e}")
            self.model = YOLO('yolov8n.pt')

    def process_frame(self, frame_bgr):
        """
        이미지(BGR)를 받아 객체를 탐지하고 결과를 반환합니다.
        """
        try:
            # 1. YOLO 추론 (로그 끄기: verbose=False)
            results = self.model(frame_bgr, verbose=False, conf=0.5)
            
            detected_items = []
            annotated_frame = frame_bgr

            # 2. 결과 그리기
            for result in results:
                annotated_frame = result.plot()
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    item_name = self.model.names[class_id]
                    detected_items.append(item_name)
            
            # 3. 텍스트 정리
            if detected_items:
                unique_items = sorted(list(set(detected_items)))
                text_result = ", ".join(unique_items)
            else:
                text_result = "nothing"
                
            return annotated_frame, text_result
            
        except Exception as e:
            print(f"❌ 프레임 처리 오류: {e}")
            return frame_bgr, "error"