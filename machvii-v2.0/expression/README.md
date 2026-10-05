# 감정 상태와 얼굴 표현

`EmotionController`는 EmotionVector의 현재값과 목표값, preset 이벤트를 관리하고 별도 loop에서 값을 보간한다. `get_current_emotion()`은 vector, preset_id, muscles를 반환한다. 현재 muscles는 빈 객체다.

API의 pipeline snapshot이 이 결과를 `/ws`로 보내고 `interface/frontend/src/context/FaceContext.jsx`가 받아 preset 표현에 사용한다. 기존 문서의 “렌더러 연결 미구현” 설명은 현재 WebSocket 수신 코드와 맞지 않아 수정했다. 목표 loop 주기를 실측 FPS로 주장하지 않는다.

[controller](emotion_controller.py) · [frontend context](../interface/frontend/src/context/FaceContext.jsx) · [API](../docs/API.md)
