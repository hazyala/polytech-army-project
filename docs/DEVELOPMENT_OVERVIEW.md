# 🚀 MACH_VII v2.0 개발 현황

## 👵 최종 목적: Silver Physical AI Sitter
본 프로젝트는 어르신의 시각 보조(약 읽기 등), 물리 케어(안경 가져오기, 등 긁어주기 등), 정서 교감을 수행하며 스스로 성장하는 AI 시터 구축을 최종 목표로 합니다.

2026.02.04

> [!NOTE]
> **가상환경 동기화 (26.02.04)**: 협업 시 패키지 충돌 방지를 위해 `environment.yml`의 모든 패키지 버전을 현재 설치된 상세 버전으로 고정했습니다. (`fastapi==0.99.1`, `pydantic==1.10.26` 등) Python 버전은 시스템 실행 환경인 `3.14`로 업데이트되었습니다.

---

## 🏗️ 레이어별 개발 진척도 요약

| 레이어 | 상태 | 주요 현황 요약 |
| :--- | :---: | :--- |
| **L1. Sensor** | 🟢 안정화 | **Shared Memory** 기반 초저지연 상태 동기화(Orientation Recovery) 및 그리퍼 카메라 좌표계 완비. |
| **L2. State** | 🟡 고도화 중 | 전역 상태 중앙 관리. `arm_status`, `focus_score` 등 관제탑 필드 추가 예정. |
| **L3. Brain** | 🟡 운용 중 | 시터 페르소나 및 자가 수정(Self-Correction) 로직 구축 예정. |
| **L4. Strategy** | 🟢 운용 중 | **ActionDispatcher** 도입으로 `RobotController` 의존성 역전 해결. `VisualServoing` 권한 격상. |
| **L5. Expression** | 🟢 완료 | **Reactive Emotion** 탑재. 행동 결과(성공/실패)에 따른 실시간 감정 반응 루프 구축 완료. |
| **L6. Embodiment** | 🟢 안정화 | 하드웨어 추상화 계층 정립. Digital Twin 기법(Shared Memory Access)으로 시뮬레이션 정합성 확보. |
| **L7. Memory** | 🟡 운용 중 | FalkorDB 기반 에피소드 저장 및 개인화 학습 엔진 가동. |

---

## 🛠️ 섹션별 상세 고도화 계획 (Advanced Roadmap)

### 🧿 1. 계층적 시각 및 정밀 인지 (Vision Assistant)
*   **Hierarchical Mapping**: 그리퍼 카메라(Main)와 월드 카메라(Sub)의 데이터를 결합하여 광역 탐색 후 정밀 파지 수행.
*   **VLM Steadycam**: 약병/처방전 읽기 시 로봇을 고정(`Soft Lock`)하여 고해상도 이미지 분석 수행 (Gemma 3 연동).
*   **Shared Memory Perception (New)**: 서버 통신 지연이나 데이터 누락(Orientation)을 극복하기 위해 물리 엔진 메모리에 직접 접근, Ground Truth 수준의 상태 동기화 달성.

### 🦾 2. 상태 관제탑 및 안전 제어 (Control Tower)
*   **ActionDispatcher (New)**: 기존 `RobotController`에 집중되었던 판단/분기 로직을 Strategy Layer로 이관. 
    *   `Intents` -> `ActionDispatcher` -> `VisualServoing` or `Motion`
    *   완전한 의존성 역전(Dependency Inversion) 실현.
*   **Safety Loop**: 신체 접촉 시 `arm_status`(STUCK)를 감시하여 즉각적인 보호 동작 및 사과 피드백 실행.
*   **Focus Score**: 영상 선명도 측정 알고리즘을 통해 인지 결과의 신뢰도 보장.

### 1. Interface Layer (사용자 접점)
- **Status**: ✅ **완료 (Phase 2 Completed)**
- **설명**: 사용자와 로봇 간의 상호작용을 담당합니다.
- **주요 컴포넌트**:
    - `API Server (FastAPI)`: 명령 수신 및 상태 방송.
    - `Frontend (React)`: 실시간 웹 인터페이스.
    - **Emotion System**:
        - `EmotionController` (Py): 감정 분석 및 프리셋 결정.
        - `WebSocket Bridge`: 실시간 상태 전송.
        - `FaceContext` (JS): SVG 표정 렌더링 및 Liveness 제어.
- **데이터 흐름**: `Chat/Voice` -> `Brain` -> `Emotion Vector` -> `Preset(Happy)` -> `WebSocket` -> `Face UI`

### 🧠 3. 성장하는 시터 (3-Mode & Self-Learning)
*   **3-Mode 책임 분리**:
    *   **Safety**: 자율성 배제, 절대 안전(헌법) 준수.
    *   **Exploration**: LLM이 DB의 실패 기록을 보고 스스로 계획을 수정하여 시도.
    *   **Exploitation**: 성공 데이터 기반의 안정적이고 숙련된 동작 재현.
*   **DB-Driven Intelligence**: FalkorDB 성공률과 현재 상황의 일치도(`db_sync_level`)에 따른 지능형 하이퍼 루프 구축.

---

## 🎭 4. Expression System Renewal (Phase 2 Completed)
*   **Reactive Emotion (New)**: 단순 명령 수행을 넘어, 행동의 결과가 감정에 영향을 미치는 순환 고리 완성.
    *   파지 성공 -> 성취감(Proud) -> 긍정적 강화
    *   파지 실패 -> 실망(Sad) -> 재시도 동기 부여
*   **Dynamic Motion Engine**: `sin` 파동 기반 실시간 모션(호흡, 떨림, 틱) 적용.

---

## 🚩 주요 마일스톤 (Milestones)

1.  **[26.02.07] 아키텍처 리팩토링 및 안정화** (완료)
    - **Dependency Inversion**: `ActionDispatcher` 구현으로 순환 참조 및 역할 혼재 해결.
    - **Shared Memory Perception**: 시뮬레이터 회전값(Orientation) 누락 문제를 메모리 직접 접근으로 해결 (L1).
    - **Physical Hard Stop**: 논리적 중단(`UserStopException`)과 물리적 고정(Hold Position)을 결합한 이중 안전장치 구축 (L6).
    - **Reactive Emotion**: 물체 소실(`Lost` -> `Confused`) 등 미세 상태 변화에 반응하는 감정 회로 구현 (L5).
2.  **[26.02] 시뮬레이션 서버(pybullet_deploy) 핵심 연동** (진행 중)
    - `sim_client` EE 카메라 및 그리퍼 피드백 수용
    - `visual_servoing` 루프 최적화 (20Hz)
3.  **[26.02] 상태 관제탑(Control Tower) 및 3-Mode 구축** (예정)
4.  **[26.03] 실버 시터 시입 시나리오(약 읽기, 등 긁기) 실증** (예정)

---
*본 문서는 실버 시터 비전을 실현하기 위한 기술적 로드맵을 포함하며, 매 수정 시 최신화됩니다.*
