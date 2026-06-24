# 🎭 Expression (표현 - 표정 엔진)

## ⚠️ 구현 상태 (Implementation Status)
- **현재 상태**: 🚧 **부분 구현 (Partial)**
    - 감정 상태를 수치적으로 관리하는 **컨트롤러**는 구현되어 있습니다.
    - 실제로 화면에 그림을 그리는 **렌더러(Renderer)** 와의 연결은 구현되지 않았습니다.

---

## 📖 개요 (Overview)
이 폴더는 로봇의 **'얼굴 표정'**을 결정하는 로직이 담긴 곳입니다.
로봇의 '기분(State)'과 '의도(Intent)'를 읽어서, 물리적인 표현 파라미터(눈 크기, 입 꼬리 올라감 정도, 고개 각도 등)로 변환합니다.

---

## 📂 파일 구조 및 상세 설명 (Structure & Files)

### 1. `emotion_controller.py` (감정 연출가)
- **주요 로직**:
    1. **명령 수신(Receive)**: `Brain/EmotionBrain`으로부터 `set_target_preset(preset_id)` 명령을 받습니다. (예: "지금 행복한 표정 지어")
    2. **목표 설정(Targeting)**: `CONFIDENCE`, `FOCUS` 등의 감정 벡터 목표치를 설정합니다.
        - `HAPPY` -> Confidence 0.8, Focus 0.5...
    3. **보간(Interpolation)**: `step(dt)` 함수가 60Hz로 실행되며 수치를 서서히 변경합니다. (갑자기 표정이 팍 바뀌지 않게 함)
    4. **파라미터 계산(Mapping)**:
        - 최종적으로 프론트엔드에 보낼 `muscles` 데이터를 계산합니다.
        - 예: `smile = (confidence - frustration)` (자신감이 높으면 웃고, 좌절하면 찡그림)
---

## ⚙️ 작동 원리 (Process Flow)

1. **이벤트 수신**: `Brain`이 "나 이제 생각 시작해(PLANNING)"라고 방송합니다.
2. **반응**: `emotion_controller`가 이를 듣고 목표 감정을 '집중 모드'로 설정합니다.
3. **루프 실행**: 백그라운드 스레드가 0.016초(60프레임)마다 돕니다.
    - 현재 감정(0.5) -> 목표 감정(1.0)으로 조금씩 이동 (0.51, 0.52...)
4. **결과 송출**: 계산된 `muscles` 데이터(눈: 0.8, 입: 0.2)를 `get_current_emotion()`을 통해 `api_server`가 가져갑니다.
5. **화면 표시**: 최종적으로 웹 브라우저(Frontend)가 이 숫자를 받아 그림을 그립니다.

---

## 🔗 상속 및 관계 (Relationships)
- **상위**: `State/SystemState` (전체 상태를 참고함)
- **하위**: `Interface/Frontend` (계산된 수치를 소비함)
