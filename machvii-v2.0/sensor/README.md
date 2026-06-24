# 👁️ Sensor Layer (Layer 1)

**Sensor Layer**는 외부 세계의 정보를 가공 없이 받아들이고, 로봇이 이해할 수 있는 데이터로 변환하는 감각 계층입니다.

---

## 🛠️ 주요 컴포넌트

### 1. VisionBridge (`vision_bridge.py`)
**[Perception Core]**
카메라 드라이버(Real/Sim)와 AI 감지 모델(YOLO)을 연결하는 허브입니다.
*   **Coordinate Transformation**: 2D 픽셀 좌표를 3D 월드 좌표(cm)로 변환합니다.
*   **Focus Score**: 이미지 선명도를 측정하여 데이터 신뢰성을 평가합니다.

### 2. Projection Logic (`projection/pybullet_projection.py`)
**[Digital Twin & Shared Memory]**
시뮬레이션 환경에서의 좌표 변환을 담당합니다. 특히 **Shared Memory Access** 기술이 적용되어 있습니다.
*   **Problem**: 시뮬레이션 서버 통신 패킷에서 로봇의 손끝 회전값(Orientation)이 누락되는 문제 발생.
*   **Solution**: 실행 중인 PyBullet 물리 서버의 공유 메모리에 직접 접근(Shared Memory)하여, 물리 엔진이 계산한 **Ground Truth 회전값**을 조회 및 동기화합니다.
*   **Result**: 로봇 팔이 어떤 각도로 꺾여 있더라도 정확한 좌표 변환이 가능합니다.

### 3. Drivers
*   `implementations/pybullet_vision.py`: 시뮬레이션 카메라 드라이버
*   `implementations/realsense_vision.py`: 리얼센스 카메라 드라이버 (예정)

---

## 🔄 좌표계 변환 흐름 (Coordinate Pipeline)
1.  **Pixel (u, v)**: YOLO가 탐지한 2D 좌표
2.  **View Space (Camera Frame)**: 카메라 기준 3D 좌표 (카메라가 보는 방향이 -Z)
3.  **Link Space (End-Effector)**: 로봇 손끝 기준 좌표 (축 정렬: View -> Link)
4.  **World Space (Robot Base)**: 로봇 바닥 기준 절대 좌표 (cm)

> **Shared Memory Check**: Step 3~4 과정에서 정확한 회전값(Orientation)이 필수적이므로, 필요 시 메모리 직접 접근이 트리거됩니다.
