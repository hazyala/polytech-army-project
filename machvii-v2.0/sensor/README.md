# 관측과 캘리브레이션

`core/`는 RealSense stream과 장비 처리, `perception/`은 VisionBridge·YOLO·PerceptionManager, `calibration_system.py`는 카메라와 로봇 좌표 변환 도구를 보관한다.

VisionBridge는 실제/가상 관측을 선택한다. PerceptionManager는 탐지와 영상 인코딩 loop를 나눠 공유 상태를 갱신한다. 모델 파일·카메라 serial·좌표 보정은 GlobalConfig와 data/calibration 경로를 사용한다. 좌표 변환에는 장비 배치에 맞춘 캘리브레이션 값이 필요하다.

## 관측을 공유하는 방법

RealSense 또는 simulator 영상 → YOLO 탐지·좌표 처리 → `system_state.perception_data` 순서로 관측을 갱신한다. `PerceptionManager`는 탐지 thread와 영상 인코딩 thread를 나누고, 메인·그리퍼 카메라 RGB/depth의 Base64 값을 공유 상태에 저장한다. agent의 장면 분석과 WebSocket 화면이 이 최신 상태를 읽는다.

[vision_bridge](perception/vision_bridge.py) · [perception_manager](perception/perception_manager.py) · [YOLO detector](perception/yolo_detector.py) · [설정](../shared/config.py)
