# 행동 기록 — FalkorDB

`falkordb_manager.py`가 localhost:6379의 graph에 연결하고 Episode·Action·Emotion 노드와 EXECUTED/STARTED_WITH/ENDED_WITH 관계를 저장한다. v2 루트의 Docker compose가 FalkorDB와 `memory/data` volume을 준비한다.

DB 미연결 시 저장은 건너뛰고 일부 조회는 기본값을 반환한다. `pipeline`이 기록하는 executed는 명령 전달 상태이며 실제 동작 성공률이 아니다. Vector DB·정책 학습은 구현되어 있지 않다.

## 저장 시점과 읽는 곳

`SystemPipeline`이 에피소드의 행동·시작/종료 감정을 모아 graph 저장을 요청한다. 저장소는 에피소드와 행동·감정 사이의 관계를 만든다. Python 상태 객체와 별개로 Docker volume의 DB에 기록한다. 실행 DB 연결은 API startup에서 준비하며 모듈을 따로 실행하는 서버 entry는 없다.

[현재 pipeline과 결과 해석](../docs/ARCHITECTURE_STATUS.md) · [저장 코드](falkordb_manager.py)
