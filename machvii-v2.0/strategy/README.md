# ♟️ Strategy Layer (Layer 4)

**Strategy Layer**는 Brain(L3)의 고수준 판단을 구체적인 행동 전략으로 변환하고, 상황에 맞는 실행 모드를 조율하는 계층입니다.

---

## 🛠️ 주요 컴포넌트

### 1. ActionDispatcher (`action_dispatcher.py`)
**[Control Tower]**
Brain의 추상적인 의도(`Intents`)를 받아 적절한 하위 모듈(`VisualServoing`, `Motion` 등)로 분배하는 **중앙 관제탑**입니다.
*   **Dependency Inversion**: 기존에 `RobotController`(L6)가 가지고 있던 판단 로직을 이곳으로 통합하여, 상위 계층이 하위 계층을 제어하는 올바른 흐름을 확립했습니다.
*   **기능**:
    *   `ActionIntent` (행동) 및 `GraspIntent` (파지) 라우팅
    *   키워드 기반 의도 파악 (한국어 지원)
    *   무한 루프 방지 및 상태 추적

### 2. VisualServoing (`visual_servoing.py`)
**[Execution Core]**
인식된 물체를 향해 로봇을 정밀하게 제어하는 시각 피드백 루프 시스템입니다.
*   **Passive Emotion Trigger**: 직접 감정 이벤트를 호출하지 않고, `SystemState`의 `arm_status`를 업데이트하여 `EmotionBrain`이 이를 감지하도록 합니다. (Centralized Control)
*   **Logic**:
    *   접근(Approach) -> 정렬(Align) -> 파지(Grasp) -> 들어올리기(Lift)
    *   YOLO 기반 실시간 좌표 보정

### 3. Policy Managers
*   `base_policy.py`: 전략의 기본 인터페이스
*   `safe_policy.py`: 절대 안전 모드 (충돌 방지 우선)
*   `explore_policy.py`: 탐험 모드 (새로운 시도 허용)

---

## 🔄 데이터 흐름
1.  **Brain (L3)** -> `ActionIntent` ("오리 잡아")
2.  **ActionDispatcher (L4)** -> `VisualServoing` 호출
3.  **VisualServoing (L4)** -> `RobotController` (L6) 명령 하달
4.  **Feedback**: 결과 -> `ActionDispatcher` -> `Broadcaster` -> `Brain` / `Expression`
