# 📁 MACH-VII v2.0 폴더 구조 및 파일 명세

이 문서는 프로젝트의 디렉토리 구조와 각 주요 파일의 역할을 정의합니다.
이 구조는 **Living Agent** 아키텍처(7 Layer Pipeline)를 그대로 반영하고 있습니다.

## 📦 전체 디렉토리 트리 (Target Architecture)

MACH_VII_v2.0/
├── 📂 sensor/               # [Layer 1] 감각 계층 (Perception)
│   ├── perception_manager.py# 감각 수집 및 상태 업데이트 관리자
│   ├── vision_bridge.py     # 하드웨어-AI 데이터 브릿지
│   ├── realsense_driver.py  # RealSense 저수준 드라이버 (AI 제거)
│   ├── realsense_vision.py  # RealSense 비전 구현체
│   └── pybullet_vision.py   # 시뮬레이션 비전 구현체
│
├── 📂 state/                # [Layer 2] 상태 계층 (Truth)
│   ├── system_state.py      # 전체 시스템 상태 (Root Object)
│   └── emotion_state.py     # 감정 상태 컴포넌트
│
├── 📂 brain/                # [Layer 3] 판단 계층 (Decision)
│   ├── logic_brain.py       # 로직 기반 판단 모듈
│   ├── emotion_updater.py   # LLM 기반 감정 업데이트
│   └── 📂 tools/            # [Tools] 에이전트 도구 (Flattened)
│       ├── robot_action.py  # 로봇 제어 도구
│       ├── vision_detect.py # 물체 탐지 도구
│       └── vision_analyze.py# VLM 영상 분석 도구
│
├── 📂 strategy/             # [Layer 4] 전략 계층 (Strategy)
│   └── strategy_manager.py  # 전역 전략 컨텍스트 및 필터 관리자
│
├── 📂 expression/           # [Layer 5] 표현 계층 (Expression)
│   └── emotion_controller.py# 감정/표정 제 프리파라미터 계산 (60Hz)
│
├── 📂 embodiment/           # [Layer 6] 구현 계층 (Embodiment)
│   ├── 📂 frontend/         # React 웹 UI (Dumb UI)
│   ├── robot_controller.py  # 로봇 행동 통합 제어기
│   ├── robot_factory.py     # 로봇 드라이버 생성 팩토리
│   ├── robot_base.py        # 로봇 추상 인터페이스
│   └── pybullet_robot.py    # 시뮬레이션 로봇 드라이버
│
├── 📂 memory/               # [Layer 7] 기억 계층 (Memory)
│   └── falkordb_manager.py  # Graph DB 관리자
│
├── 📂 shared/               # 공용 모듈
│   ├── pipeline.py          # [Core] 7단계 단방향 파이프라인 매니저
│   ├── config.py            # [Central] PathConfig 및 GlobalConfig
│   └── state_broadcaster.py # [Sync] 상태 전파 이벤트 버스
│
├── 📂 interface/            # 외부 인터페이스 (Interface)
│   ├── api_server.py        # FastAPI API/WS 서버 (Flattened)
│   └── pybullet_client.py   # 시뮬레이션 서버 통신 클라이언트
│
├── main.py                  # [Root] 시스템 실행 진입점
├── test_dofbot_status.py    # [Test] DOFBOT 종합 상태 모니터링 테스트
├── docker-compose.yml       # [Conf] DB 컨테이너 설정
└── environment.yml          # [Conf] Conda 환경 설정

## 🔍 주요 디렉토리별 역할 상세

### 1. `sensor/`
*   **역할**: 하드웨어로부터 Raw Data를 수집합니다.
*   **주의**: 데이터를 해석하거나 가공하지 않고 상위 레이어로 전달만 합니다.

### 2. `state/`
*   **역할**: 수집된 데이터를 통합하여 "현재 상황"을 정의합니다.
*   **핵심 파일**: `system_state.py` (전체 시스템의 상태를 담는 객체)

### 3. `brain/`
*   **역할**: "무엇을 할 것인가"를 결정합니다.
*   **특징**: 하드웨어를 직접 제어하지 않고 `Intent`(의도)만 생성합니다.
❌ 포함되면 안 되는 것
모터 각도 계산
UI 상태 직접 변경
하드웨어 API 호출

### 4. `strategy/`
*   **역할**: Brain의 단기적 판단이 장기적 목표/성향에 위배되지 않는지 검사합니다.

### 5. `expression/`
*   **역할**: 추상적인 `Intent`를 구체적인 물리량(각도, 속도)으로 변환합니다.
*   **특징**: 60fps 루프가 돌아가며 부드러운 보간(Interpolation)을 수행합니다.

### 6. `embodiment/`
*   **역할**: 최종 물리량을 실제로 화면에 그리거나 모터를 움직입니다.
*   **규칙**: 자체적인 판단 로직을 절대 포함하지 않습니다. (UI is Dumb)

### 8. `docs/` (프로젝트 기록 및 현황)
*   **역할**: 프로젝트의 아키텍처와 개발 진척도를 기록하는 중앙 저장소입니다.
*   **핵심 파일**:
    *   `DEVELOPMENT_OVERVIEW.md`: 레이어별 리팩토링 및 개발 현황 대시보드
    *   `ARCHITECTURE_STATUS.md`: 7계층 아키텍처 설계 및 실제 적용 현황
    *   `PROJECT_STRUCTURE.md`: 현재 문서 (폴더 및 파일 명세)

### 9. `sensor/` 상세 구조 (Layer 1 & 2)
*   **`core/`**: 비전 베이스 클래스(`vision_base.py`) 및 하드웨어 드라이버(`realsense_driver.py`).
*   **`implementations/`**: 환경별 구현체(`realsense_vision.py`, `pybullet_vision.py`).
*   **`perception/`**: YOLO 탐지(`yolo_detector.py`), 좌표 중계(`vision_bridge.py`) 및 관리자(`perception_manager.py`).
    *   `vision_bridge.py`는 실물 모드에서 **색상 마커 탐지**(`RedTapeDetector`)를 YOLO 탐지와 병행하여 `red_marker` 타겟을 자동 추가합니다.
*   **`projection/`**: 정밀 좌표 투영 알고리즘 수식 모듈.
*   **`calibration_system.py`**: HSV 기반 빨간 테이프 마커 검출(`RedTapeDetector`) 및 카메라-로봇 Affine 변환 행렬 관리(`CameraCalibrator`, `MultiCameraCalibrator`).
