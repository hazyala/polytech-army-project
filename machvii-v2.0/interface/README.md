# 외부 인터페이스

`backend/api_server.py`는 FastAPI HTTP·WebSocket entry다. startup에서 인식·표현·로봇 loop를 시작하고 pipeline component와 memory 연결을 등록한다. `backend/sim_client.py`는 별도 PyBullet 서버와 연결한다.

실행은 v2 루트의 `python main.py`를 사용한다. frontend는 별도 npm 개발 서버다. backend 패키지 폴더에서 직접 실행하면 상위 `shared` 등 import 경로가 맞지 않을 수 있다.

[API 계약](../docs/API.md) · [Frontend 실행](frontend/README.md) · [v2 실행 환경](../README.md)
