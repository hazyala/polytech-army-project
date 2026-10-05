# Army 2D Simulator Prototype

Streamlit 화면에서 WebRTC 카메라 프레임을 YOLO로 분석하고 LangChain agent가 텍스트에 반응하는 초기 실험. `app/main.py`가 session_state에 영상·탐지 결과·메시지를 보관하고 상태별 GIF를 표시한다.

`app/vision.py`는 YOLO 영상 처리, `app/agent.py`는 모델·도구 연결이다. v2의 FastAPI/WebSocket 시스템과 별도로 실행한다.

```bash
cd army-simulator-proto
docker compose up --build
```

저장소 루트에서 실행한다. Dockerfile의 Streamlit entry와 compose 포트·Ollama 연결을 확인한다. LLM 서버와 모델은 별도로 필요하다. 이 명령은 장비·외부 서버가 준비된 환경용이며 현재 호출 성공을 검증한 것은 아니다.

브라우저 카메라 권한과 WebRTC 환경이 필요하다. 자동 탐지에서는 중복·빈 탐지 결과를 걸러내고 YOLO label 텍스트를 우선 전달한다. 이 프로토타입의 UI 상태가 실제 로봇 제어 결과를 나타내지는 않는다.
