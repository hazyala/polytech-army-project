# 의도 분배와 visual servoing

`ActionDispatcher`는 ActionIntent·GraspIntent를 동작 처리로 분배한다. `visual_servoing.py`는 관측과 로봇 상태를 읽어 접근·정렬·파지·들어올리기 단계의 동작을 처리한다. `grasp_planner.py`, `grasp_strategy.py`는 grasp 계획과 실행 경로를 다룬다.

`StrategyManager`는 rule_based/memory_based에 따른 risk_level·allow_explore context와 키워드 필터를 관리한다. `safe_policy.py`, `explore_policy.py`, `base_policy.py`는 전략 구현·경계를 보관한다.

[ActionDispatcher](action_dispatcher.py) · [VisualServoing](visual_servoing.py) · [StrategyManager](strategy_manager.py) · [실행·기억 경계](../docs/ARCHITECTURE_STATUS.md)
