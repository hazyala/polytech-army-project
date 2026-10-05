# 로봇 driver와 제어

`robot_base.py`의 공통 경계를 PyBullet·DOFBOT driver가 구현한다. `robot_factory.py`는 대상별 driver를 만들고 `robot_controller.py`는 driver 선택·제어 loop·상태를 관리한다. `motion_controller.py`는 동작 명령 처리에 사용된다.

DOFBOT은 별도 서버와 HTTP·Socket.IO로 연결하고 PyBullet도 별도 simulator 서버를 사용한다. 이 폴더가 모터·물리 엔진 전체를 자체 실행하는 것으로 보지 않는다. 서버 주소와 포트는 [GlobalConfig](../shared/config.py)를 확인한다.

긴급 정지는 현재 driver의 emergency_stop을 호출한다. 지원 pose 필드와 하드웨어 정지 동작은 driver별로 다르므로 실제 로봇과 가상 로봇의 동작이 완전히 같다고 설명하지 않는다. 초기 연결·캘리브레이션 조건은 [v2 실행](../README.md)을 본다.

[robot_factory](robot_factory.py) · [robot_controller](robot_controller.py) · [dofbot_robot](dofbot_robot.py) · [pybullet_robot](pybullet_robot.py)
