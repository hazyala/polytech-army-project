# MACH-VII v2

자연어 명령과 카메라 관측을 로봇 동작·얼굴 상태·행동 기록에 연결하는 실험 시스템.

## 구현한 경로

`LogicBrain`은 ChatOllama와 LangChain structured-chat agent를 사용해 vision·grasp·robot 도구를 선택한다. 전략과 visual servoing 모듈이 동작을 처리하고, embodiment driver는 PyBullet 서버 또는 DOFBOT 서버에 요청한다. API startup은 인식·감정·로봇 loop를 시작하고 FalkorDB에 연결한다.

React 화면은 `/ws` 스냅샷의 표정·로봇·영상·전략 상태를 읽는다. 백엔드가 0.016초 sleep으로 전송 loop를 돌지만 이는 목표 주기이고 실측 60 FPS 보장은 아니다. LangGraph는 환경 export에 포함되어 있지만 현재 LogicBrain의 실행기는 LangChain `initialize_agent`다.

## 폴더의 책임

| 위치 | 역할 |
|---|---|
| `sensor/` | RealSense·가상 카메라 bridge, YOLO, 좌표·캘리브레이션 처리 |
| `state/`, `shared/` | 상태, DTO, intent, pipeline와 broadcaster |
| `brain/`, `brain/tools/` | 모델 호출, agent와 도구 |
| `strategy/` | 전략 필터, action dispatcher, visual servoing |
| `expression/` | 감정 상태·표현 갱신 |
| `embodiment/` | 로봇 driver 선택과 제어 loop |
| `memory/` | FalkorDB graph 저장·조회 |
| `interface/backend/` | FastAPI entry, simulator client |
| `interface/frontend/` | React 얼굴과 제어 UI |
| `참고/` | 외부 로봇·PyBullet 참고 코드 |

[현재 아키텍처](docs/ARCHITECTURE_STATUS.md)는 코드 경로와 제약을 설명한다. [설계 원칙](docs/ARCHITECTURE_GUIDELINES.md)과 [비전 기록](docs/PROJECT_VISION.md)은 지향점이며 구현 보증과 구분한다.

## 실행 전 확인

`environment.yml`은 Python 3.10.19 Windows Conda export다. Windows build string과 로컬 prefix가 있어 다른 OS의 범용 lockfile이 아니다. 설치된 LangChain/FastAPI/Pydantic 조합, PyTorch·RealSense SDK와 장비를 확인해야 한다.

```bash
conda env create -f environment.yml
conda activate MACH_VII_v2.0
docker compose up -d
python main.py
```

위 명령은 `machvii-v2.0/`에서 실행한다. Docker compose는 FalkorDB만 시작하고 모델·카메라·로봇 서버를 시작하지 않는다. 의존성 해결이나 외부 연결이 실패하면 정상 실행으로 보지 않는다.

| 연결 | 코드의 현재 값 / 위치 |
|---|---|
| API | 8000, `main.py` |
| Frontend | Vite 기본 5173, WS `ws://localhost:8000/ws` |
| FalkorDB | localhost:6379, `memory/falkordb_manager.py` |
| PyBullet | localhost:5000, `GlobalConfig.PYBULLET_PORT` |
| DOFBOT | 192.168.25.100:5000, `GlobalConfig` |
| VLM | `GlobalConfig.VLM_ENDPOINT`, gemma3:27b |

기존 문서의 PyBullet 5001 안내와 달리 현재 config는 5000이다. 주소·장비 serial은 `shared/config.py`의 상수이며 환경변수로 자동 치환되는 값이 아니다. 이 문서 정비에서 설정 파일은 바꾸지 않았다.

다른 터미널에서 [frontend](interface/frontend/README.md)를 실행한다. 명령 입력은 `python manual_client.py`, 상태·영상 확인은 `python vision_debug.py`에 별도 entry가 있다. 실제 장비 연결 없이 이를 검증했다고 주장하지 않는다.

## API와 구현 메모

`POST /api/request`는 command/config_change/emergency DTO를 받는다. 레거시 `/api/command`, `/api/config`도 남아 있다. 입력·응답·정지 경로 차이는 [API](docs/API.md)를 본다.

`SystemPipeline`은 intent를 전략으로 걸러내고 상태와 표현을 갱신한 뒤 에피소드를 저장한다. 저장 결과 `executed`는 명령 하달 기록이며 실제 grasp 성공 판정이 아니다. Graph DB에는 Episode·Action·Emotion 관계가 저장되며 Vector DB나 자동 정책 학습이 구현된 것으로 소개하지 않는다.
