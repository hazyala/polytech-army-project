# 공유 상태

`SystemState`는 perception_data, 로봇 상태, intent와 arm 관련 상태를 다른 loop에서 공유한다. WebSocket snapshot과 전략·감정 처리가 이 값을 참조한다. 실제 센서 측정과 기본 상태 필드를 같은 실측값으로 보지 않는다.

`EmotionVector`의 현재 필드는 focus, effort, confidence, frustration, curiosity 다섯 개다. update는 값을 0~1 범위로 제한한다. 기존 README의 P/A/D 세 필드 설명과 달리 현재 코드는 변형된 5차원 상태를 사용한다.

[system_state.py](system_state.py) · [emotion_state.py](emotion_state.py) · [snapshot 경계](../docs/ARCHITECTURE_STATUS.md)
