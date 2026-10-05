# 관측과 캘리브레이션

`core/`는 RealSense stream과 장비 처리, `perception/`은 VisionBridge·YOLO·PerceptionManager, `calibration_system.py`는 카메라와 로봇 좌표 변환 도구를 보관한다.

VisionBridge는 실제/가상 관측을 선택한다. PerceptionManager는 탐지와 영상 인코딩 loop를 나눠 공유 상태를 갱신한다. 모델 파일·카메라 serial·좌표 보정은 GlobalConfig와 data/calibration 경로를 사용한다. 설정에 있는 임시 offset을 정식 calibration 완료로 소개하지 않는다.

[vision_bridge](perception/vision_bridge.py) · [perception_manager](perception/perception_manager.py) · [YOLO detector](perception/yolo_detector.py) · [설정](../shared/config.py)
