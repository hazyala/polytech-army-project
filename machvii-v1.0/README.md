# MACH-VII v1 — 카메라와 로봇 도구를 연결한 Streamlit agent

대화 입력을 LangChain agent에 전달하고 물체 탐지·장면 설명·로봇 이동·표정·기억 도구를 호출하는 로봇 실험이다. 화면은 Streamlit, 카메라는 RealSense 또는 외부 PyBullet 서버, 모델은 Ollama를 사용한다.

## 구현한 흐름

1. `main.py`가 화면·대화·표정 상태를 `st.session_state`에 보관하고 `MachEngine`을 만든다.
2. `VisionSystem`이 RGB·depth를 읽고 YOLO 탐지 결과·좌표·현재 영상을 갱신한다. 영상 loop는 별도 thread에서 실행한다.
3. `MachEngine`이 `gemma3:27b`와 structured-chat agent를 연결한다. 대화 맥락은 `ConversationSummaryBufferMemory`로 전달한다.
4. agent가 `vision_detect`, `vision_analyze`, `find_location`, `robot_action`, `emotion_set`, `memory_save`, `memory_load` 중 도구를 선택한다.
5. 표정 도구는 눈·입·색상 값을 바꾸고 `face_renderer.py`가 SVG 얼굴을 그린다. 기억 도구는 FalkorDB를 조회·저장한다.

## 로봇·시뮬레이터 연결

`robot_action.py`는 화면의 `sim_mode`에 따라 요청 대상을 고른다. PyBullet 경로는 mm 좌표를 m로 바꿔 `http://localhost:5000/set_pos`로 보내고, 실물 경로는 코드에 지정된 로봇 서버의 `/robot/action`으로 보낸다. RealSense 대신 시뮬레이터 영상을 읽는 경로도 `VisionSystem`에 있다.

좌표계, 실물 로봇팔 각도와 작업 공간 보정은 남아 있는 작업이다. 물체 좌표를 받아 외부 서버에 이동 요청을 보내는 단계까지 연결한 버전이다.

## 실행

`machvii-v1.0/`에서 다음 명령을 사용한다.

```bash
python -m pip install -r code/requirements.txt
streamlit run code/main.py
```

Ollama 주소·모델은 `code/engine.py`, 로봇 주소는 `code/tools/robot_action.py`에 있다. 기억 기능에는 localhost:6379의 FalkorDB가 필요하다. YOLO 모델 경로는 `data/models/yolo11n.pt`이며 카메라 모드에는 RealSense SDK·장비, simulator 모드에는 별도 PyBullet HTTP 서버가 필요하다.

| 위치 | 맡는 일 |
|---|---|
| [code/main.py](code/main.py) | Streamlit 입력·화면·모드 선택 |
| [code/engine.py](code/engine.py) | agent·대화 맥락·영상 thread |
| [code/vision.py](code/vision.py) | RGB-D·YOLO·좌표 계산 |
| [code/tools](code/tools/) | 모델이 호출하는 도구와 외부 서버 client |
| [code/docs](code/docs/README.md) | 프로젝트 이름·실행 메모·설정 기록 |

FastAPI·React 버전은 [MACH-VII v2](../machvii-v2.0/README.md)에 있다.
