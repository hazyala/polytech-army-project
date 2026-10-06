# 설정·계약·상태 중계

| 파일 | 맡는 일 |
|---|---|
| [config.py](config.py) | PathConfig 경로와 GlobalConfig 모델·장비·서버 상수 |
| [ui_dto.py](ui_dto.py) | 통합 사용자 요청, 설정 enum, WebSocket snapshot |
| [pipeline.py](pipeline.py) | 전략 필터, 감정 목표, action_intent 전파, 에피소드 저장 |
| [intents.py](intents.py) | ActionIntent와 문자열 intent 변환 |
| [state_broadcaster.py](state_broadcaster.py) | 이벤트 발행·구독과 상태 snapshot |
| [filters.py](filters.py) | 공용 필터 |

`SystemPipeline`은 등록된 component를 사용하고 state·strategy·memory를 직접 참조한다. 현재 GlobalConfig 값은 환경변수 자동 치환이 아니라 Python 상수다.

[HTTP/WS 계약](../docs/API.md)과 [실제 경계](../docs/ARCHITECTURE_STATUS.md)에 공통 규약을 모아 중복 설명을 줄인다.
