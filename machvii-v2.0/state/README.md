# 공유 상태

`SystemState`는 perception_data, 로봇 상태, intent와 arm 관련 상태를 다른 loop에서 공유한다. WebSocket snapshot과 전략·감정 처리가 이 값을 참조한다.

`EmotionVector`의 현재 필드는 focus, effort, confidence, frustration, curiosity 다섯 개다. update는 값을 0~1 범위로 제한한다.

## 함께 읽는 값

- `perception_data`: 탐지 결과와 관측 정보.
- `RobotStatus`: 이동 여부·모드, 팔 상태·그리퍼·unsafe 표시.
- `last_frame_base64` 등: 인코딩된 메인·그리퍼 카메라 영상.
- `current_intent`: 현재 행동 의도.

각 모듈은 전역 `system_state`를 갱신·참조한다. `to_dict()`는 화면 snapshot에 쓸 감정·로봇·관측·intent 값을 묶는다. `battery_level`·`focus_score`에는 기본값이 있으므로 필드 값의 생성 경로를 확인해 사용한다.

[system_state.py](system_state.py) · [emotion_state.py](emotion_state.py) · [snapshot 경계](../docs/ARCHITECTURE_STATUS.md)
