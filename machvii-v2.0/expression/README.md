# 감정 상태와 얼굴 표현

`EmotionController`는 EmotionVector의 현재값과 목표값, preset 이벤트를 관리하고 별도 loop에서 값을 보간한다. `get_current_emotion()`은 vector, preset_id, muscles를 반환한다. 현재 muscles는 빈 객체다.

API의 pipeline snapshot이 이 결과를 `/ws`로 보내고 `interface/frontend/src/context/FaceContext.jsx`가 받아 preset 표현에 사용한다.

## 화면까지 전달하는 값

agent·pipeline에서 받은 감정 이벤트 → 목표 EmotionVector/preset → loop 보간 → WebSocket snapshot → React 얼굴 표현 순서다. 벡터는 focus·effort·confidence·frustration·curiosity를 사용하며 얼굴 UI는 전달된 preset을 읽는다. `muscles`를 이용한 개별 얼굴 근육 제어는 현재 빈 값이다.

[controller](emotion_controller.py) · [frontend context](../interface/frontend/src/context/FaceContext.jsx) · [API](../docs/API.md)
