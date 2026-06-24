# 🧠 MACH-VII v2.0
### Living Agent / Embodied Robot System

**MACH-VII v2.0**은 단순히 명령을 수행하는 로봇이 아니라, **감각하고, 상태를 인식하고, 판단하며, 전략적으로 행동하고, 그 결과를 기억하는** **Living Agent(살아있는 에이전트)**를 구현하기 위한 아키텍처 기반 프로젝트입니다.

> 이 프로젝트의 목표는 **“움직이는 UI”가 아니라 “판단 구조를 가진 존재”**를 만드는 것입니다.

---

## ✨ 이 프로젝트로 무엇을 할 수 있나요?

사용자는 자연어로 에이전트에게 말을 겁니다.

> 🗣️ "앞에 있는 오리를 잡아봐"
> 🗣️ "너 지금 뭐 해?"
> 🗣️ "기분이 어때?"

에이전트는 이를 즉각적인 반응이 아닌, 다음의 순환 과정을 거쳐 처리합니다:

1.  현재 환경을 **감각(Sense)**하고
2.  자신의 **상태(State)**를 정의하고
3.  무엇을 할지 **판단(Decide)**하고
4.  성향과 모드에 맞게 **전략(Strategy)**을 조정한 뒤
5.  **표정과 움직임(Expression)**으로 표현하고
6.  그 결과를 **기억(Memory)**합니다.

즉, **입력 → 출력**이 아니라 **경험 → 판단 → 표현 → 학습**의 순환 구조를 가집니다.

---

## 🧭 핵심 설계 철학 (Core Philosophy)

### 1. 단방향 파이프라인 (One-way Pipeline)
`Sensor` → `State` → `Brain` → `Strategy` → `Expression` → `Embodiment` → `Memory`

*   데이터와 결정은 **절대 역류하지 않습니다.**
*   하위 계층은 상위 계층의 존재를 모릅니다.
*   **“UI가 판단을 바꾸는”** 구조는 존재하지 않습니다.

### 2. 레이어 독립성 (Layer Independence)
각 레이어는 자신의 책임만 가집니다.

| 레이어 | 책임 |
| :--- | :--- |
| **Sensor** | 유의미한 해석 없는 순수 감각 수집 |
| **State** | 현재 상황과 에이전트 상태 정의 |
| **Brain** | 행동 결정 및 논리적 판단 |
| **Strategy** | 장기적 성향 및 모드(안전/탐험) 조율 |
| **Expression** | 추상적 의도를 물리적 움직임으로 변환 |
| **Embodiment** | 최종 렌더링 및 물리 하드웨어 구현 |
| **Memory** | 모든 과정의 기록 및 학습 데이터 제공 |

### 3. 관측 가능성 (Observability)
*   모든 판단과 행동은 **로그와 데이터로 추적 가능**해야 합니다.
*   “왜 저 행동을 했는지”를 **사후 분석**할 수 있어야 합니다.

---

## 🏗️ 시스템 아키텍처 개요

이 시스템은 7개의 레이어로 구성됩니다.

### 1️⃣ Sensor Layer — 감각 계층
*   외부 세계를 ‘있는 그대로’ 받아들입니다.
*   Camera, Microphone, 키보드/마우스 입력
*   **Shared Memory Perception**: 시뮬레이터 메모리 직접 접근을 통한 초정밀 상태 동기화
*   **출력**: `SensorFrame`

### 2️⃣ State Layer — 상태 계층
*   지금 이 시스템이 어떤 상태인지 정의합니다.
*   위험도, 존재 감지, 시스템 상태
*   “좋다/싫다” 판단 없음
*   **출력**: `SystemState`

### 3️⃣ Brain / Policy Layer — 판단 계층
*   무엇을 할지 결정합니다.
*   LLM 기반 논리 판단, 룰 기반 로직, 감정 코어
*   **출력**: `PolicyDecision` (예: GREET, IDLE, RETREAT)

### 4️⃣ Strategy Layer — 전략 계층
*   판단을 행동으로 옮기고, 성향과 모드에 맞게 조율합니다.
*   **ActionDispatcher**: 중앙 행동 관제 및 의존성 주입 (DI)
*   **VisualServoing**: 시각 기반 정밀 제어 (PyBullet + DOFBOT 실물 모드 지원)
    *   실물 모드: 5Hz 루프 + Gain 0.5 (통신 지연 보상)
    *   시뮬레이션: 10Hz 루프 + Gain 0.8 (고속 피드백)
*   Safe / Explore / Combat 모드
*   **출력**: `StrategyState`

### 5️⃣ Expression Layer — 표현 계층
*   의도를 물리적 움직임으로 변환합니다.
*   **EmotionController (Backend)**: 상태 벡터 분석 및 16종의 동적 프리셋(Excited, Mischievous 등) 결정
*   **FaceContext (Frontend)**: 결정된 프리셋의 고유 모션(떨림, 호흡, 회전)을 60fps로 실시간 렌더링 (Liveness 포함)
*   **출력**: `ExpressionFrame` (WebSocket Packet)

### 6️⃣ Embodiment Layer — 구현 계층
*   보이거나 움직이게 합니다.
*   React 기반 얼굴 UI, 실제 로봇 하드웨어 드라이버
*   **계산 로직 ❌** (순수 실행)

### 7️⃣ Memory Layer — 기억 계층
*   모든 결과를 기록합니다.
*   성공 / 실패 / 상태 변화
*   Vector DB, 로그 시스템 → **학습의 재료 제공**

### 8️⃣ Intelligent Eye (Active Perception)
*   **지능형 능동 인지**: 단순 관측을 넘어, VLM의 '인지 확신도(Task Confidence)'를 기반으로 로봇이 스스로 가장 잘 보이는 위치를 찾아가는 시스템입니다.
*   **7-Layer 협업**: Perception(L1)의 선명도 측정 + Strategy(L4)의 상태 기계(`SCANNING`, `AUTO_FOCUS`, `VLM_CHECK`) + Expression(L5)의 물리적 정렬이 결합됩니다.
*   **고속 피드백**: 상위 레이어의 간섭 없이 독립적인 자율 신경계처럼 동작하며, 인식 불확실 시 스스로 각도를 수정(Retry)합니다.

### 9️⃣ System Stability & Concurrency
*   **RLock Hardening**: 모든 커널 싱글톤 및 컨트롤러에 `threading.RLock`을 적용하여 동일 스레드 내 재귀 호출로 인한 데드락을 원천 차단했습니다.
*   **Async-Safe Broadcasting**: 고속 통신 루프 내에서 브로드캐스트 호출을 락 구간 외부로 분리하여 시스템 응답성을 극대화했습니다.
*   **Physical Hard Stop**: 긴급 정지 시 논리적 중단뿐만 아니라, 물리 엔진에 현재 위치 유지(Hold) 명령을 전송하여 관성에 의한 사고를 방지합니다.
*   **Optimized Startup**: PyBullet 커넥션 타임아웃 최적화(3s)를 통해 시뮬레이션 환경 유무와 관계없이 빠른 시스템 부팅을 보장합니다.

---

## 📁 프로젝트 구조

폴더 구조 자체가 아키텍처를 반영합니다.

```
MACH_VII_v2.0/
├── sensor/          # [Layer 1] 감각 수집 (Shared Memory Vision)
├── state/           # [Layer 2] 상태 정의 (SystemState, Emotion)
├── brain/           # [Layer 3] 판단 및 로직 (LogicBrain, LLM)
│   └── tools/       # [Tools] 에이전트 가용 도구 (Flattened)
├── strategy/        # [Layer 4] 전략 및 실행 (ActionDispatcher, VisualServoing)
├── expression/      # [Layer 5] 표현 엔진 (EmotionController)
├── embodiment/      # [Layer 6] 구현 계층 (Drivers)
│   └── frontend/    # [View] React Face UI (Dumb UI)
├── memory/          # [Layer 7] 기억 및 로그 (FalkorDB)
├── shared/          # 공용 모듈 (Pipeline, Config, Broadcaster)
├── interface/       # 외부 인터페이스 (api_server, Flattened)
├── data/            # 모델, 로그 등 데이터 저장소
├── docs/            # 설계 및 운영 문서
├── main.py          # [Entry] 시스템 진입점
├── docker-compose.yml # [DB] FalkorDB 실행 설정
└── environment.yml  # [Env] Conda 환경 설정
```

---

## 🚀 실행 방법

### 0. 중요: 포트 설정

**PyBullet 시뮬레이션 서버와 DOFBOT 실물 로봇 서버의 포트 충돌을 방지하기 위해 다음과 같이 설정되어 있습니다:**

- **PyBullet 서버**: `http://localhost:5001` (기본 5000에서 변경됨)
- **DOFBOT 서버**: `http://localhost:5000` (DOFBOT_ROBOT_ARM-main/main.py)
- **MACH_VII API**: `http://localhost:8000`

> **주의**: PyBullet 시뮬레이션 서버를 사용하는 경우, 해당 서버도 **포트 5001**로 실행해야 합니다.

### 1. 필수 환경
*   **Anaconda / Miniconda**
*   **Node.js v18+**
*   **Python 3.10+**
*   **(선택) DOFBOT 실물 로봇** - 실물 모드 사용 시
*   **(선택) Intel RealSense 카메라** - 실물 비전 사용 시

### 2. Backend (Conda + Docker)
```bash
# 1. 데이터베이스 실행 (Docker 필수, 종료 후에도 데이터 보존됨)
docker-compose up -d

# 2. 가상환경 생성 및 활성화
conda env create -f environment.yml
conda activate MACH_VII_v2.0


### Conda 환경 설정 오류 시 해결 방법
```bash
# 1. Conda 가상환경 생성
conda create -n MACH_VII_v2.0 python=3.10 pip -y
conda activate MACH_VII_v2.0
conda install -c conda-forge numpy scipy mkl pybullet -y
```

```bash
# 2. 라이브러리 설치
python -m pip install aiohttp altair annotated-doc annotated-types anyio attrs bidict blinker cachetools certifi charset-normalizer click colorama contourpy cycler dataclasses-json fastapi==0.99.1 fonttools fsspec gitpython greenlet h11 httpx huggingface-hub jinja2 jsonschema kiwisolver langchain langchain-community langchain-core langgraph langsmith matplotlib networkx opencv-python orjson packaging pandas pillow polars protobuf psutil pyarrow pydeck pyparsing pyrealsense2 python-dotenv python-socketio pytz pyyaml redis requests safetensors sqlalchemy starlette streamlit sympy tenacity tokenizers tqdm transformers typing-extensions ultralytics uvicorn watchdog websockets websocket-client yarl zstandard
```

```bash
# 3. 충돌 가능성 있는 라이브러리 설치
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```


### 3. Frontend (React)
```bash
cd interface/frontend

# 패키지 설치
npm install

# 실행
npm run dev
```
> UI: `http://localhost:5173`


### 🛠️ Utilities & Debug Tools
시스템의 각 구성 요소를 독립적으로 테스트하거나 상태를 모니터링하기 위한 도구들입니다.

*   **Terminal Client (채팅/설정 인터페이스)**: 터미널에서 직접 시스템 설정을 변경(가상/실물 로봇 등)하고, 에이전트와 자연어로 명령을 보냅니다. 에이전트 응답과 사고는 main.py에서 처리 되니, main.py로그를 확인해주세요.
    ```bash
    python manual_client.py
    ```
*   **Vision Debug (인지 시각화)**: 메인 서버에서 처리되는 영상 데이터와 YOLO 탐지 결과, 보정된 3D 좌표 정보를 실시간 뷰어로 확인합니다.
    ```bash
    python vision_debug.py
    ```

---

## 📏 개발 규칙 (매우 중요)

### NO REVERSE FLOW
*   상위 레이어가 하위 레이어를 import 하는 것은 **절대 금지**입니다.

### STRICT INTERFACES
*   각 레이어는 **DTO 기반 통신**만 허용됩니다.

### UI IS DUMB
*   **UI는 절대 판단하지 않습니다.** 오직 그리기만 합니다.

### CENTRALIZED PATH MANAGEMENT
*   모든 파일 및 디렉토리 경로는 `shared/config.py`의 `PathConfig`를 참조해야 합니다.
*   하드코딩된 문자열 경로나 `os.path` 직접 사용을 지양하고 `pathlib` 기반의 `PathConfig`를 사용하십시오.

---

## 🎯 이 프로젝트가 지향하는 것

*   챗봇 ❌
*   애니메이션 캐릭터 ❌
*   명령형 로봇 ❌
*   **👉 판단 구조를 가진 에이전트**
*   **👉 확장 가능한 인지 아키텍처**
*   **👉 연구·실험·실제 로봇까지 이어지는 기반**
