# 로봇 driver와 제어

`robot_base.py`의 공통 경계를 PyBullet·DOFBOT driver가 구현한다. `robot_factory.py`는 대상별 driver를 만들고 `robot_controller.py`는 driver 선택·제어 loop·상태를 관리한다. `motion_controller.py`는 동작 명령 처리에 사용된다.

DOFBOT은 별도 서버와 HTTP·Socket.IO로 연결하고 PyBullet도 별도 simulator 서버를 사용한다. 서버 주소와 포트는 [GlobalConfig](../shared/config.py)를 확인한다.

긴급 정지는 현재 driver의 emergency_stop을 호출한다. pose 필드와 정지 요청은 각 driver의 외부 서버 계약을 따른다. 초기 연결·캘리브레이션 조건은 [v2 실행](../README.md)을 본다.

## 제어 연결

전략 모듈의 좌표·관절·그리퍼 요청을 공통 driver 메서드로 받는다. factory가 선택한 driver가 이를 대상 서버의 요청으로 바꾸고, controller는 연결 대상·제어 loop·현재 상태를 관리한다. 실제 모터 구동과 simulator 물리 계산은 각각의 외부 서버가 담당한다.

[robot_factory](robot_factory.py) · [robot_controller](robot_controller.py) · [dofbot_robot](dofbot_robot.py) · [pybullet_robot](pybullet_robot.py)
