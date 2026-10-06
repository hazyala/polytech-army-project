# MACH-VII v1 개발 메모

MACH-VII의 별명은 맹칠, 영어 이름은 Mark다. Gemma 기반 로봇 조수라는 초기 컨셉에서 카메라 탐지·대화·도구 실행·SVG 표정을 한 Streamlit 화면에 연결했다.

## 문서와 소스

- [v1 README](../../README.md): 구현한 흐름과 실행 조건.
- [memo.txt](memo.txt): Ollama·Streamlit·FalkorDB·PyBullet 개발 명령 메모. 경로와 환경 이름은 개발 환경에 맞춰 사용한다.
- [config.txt](config.txt): 초기 설정 기록.
- [engine.py](../engine.py): 모델, 요약 대화 memory, agent 도구와 system instruction.
- [tools](../tools/): 탐지·장면 분석·좌표 조회·로봇 명령·표정·graph 기억.

모터 이동은 외부 로봇 서버가 처리하고 이 코드가 HTTP 요청을 보낸다. RealSense 모드는 장비에서 RGB-D를 읽고 simulator 모드는 별도 PyBullet 서버에서 영상을 받는다. 이동형 Maqueen 플랫폼은 초기 하드웨어 구상이며 현재 v1 도구의 실행 경로는 로봇팔과 simulator다.
