# 의도 분배와 visual servoing

`ActionDispatcher`는 ActionIntent·GraspIntent를 동작 처리로 분배한다. `visual_servoing.py`는 관측과 로봇 상태를 읽어 접근·정렬·파지·들어올리기 단계의 동작을 처리한다. `grasp_planner.py`, `grasp_strategy.py`는 grasp 계획과 실행 경로를 다룬다.

`StrategyManager`는 rule_based/memory_based에 따른 risk_level·allow_explore context와 키워드 필터를 관리한다. `safe_policy.py`, `explore_policy.py`, `base_policy.py`는 전략 구현·경계를 보관한다.

## 행동을 실제 명령으로 바꾸는 부분

`ActionDispatcher`는 broadcaster의 intent를 받아 정지·인사·들어올리기·상대 이동·그리퍼와 grasp 경로로 분배한다. grasp 경로는 공유 관측에서 대상 정보를 읽고 visual servoing/전략 처리로 이어진다. 단순 이동은 현재 pose를 읽어 목표 좌표를 만들고 robot driver를 호출한다. 이 폴더는 자연어 응답 생성보다 intent 이후의 동작 선택을 맡는다.

[ActionDispatcher](action_dispatcher.py) · [VisualServoing](visual_servoing.py) · [StrategyManager](strategy_manager.py) · [실행·기억 경계](../docs/ARCHITECTURE_STATUS.md)
