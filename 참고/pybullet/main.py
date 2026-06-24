'''
2026.01.08
- Streamlit UI 레이아웃 개선
- 조인트 슬라이더 제어 기능 추가
- Flask, Pybullet 모듈화

2026.01.09
- 로봇 속도 조절 슬라이더 추가

2026.01.10
- 오브젝트 선택 제어 기능 추가

2026.01.13
- Gripper 제어 기능 추가

2026.01.14
- Depth RAW 데이터 반환 기능 추가
- 오브젝트 고정 기능 추가

2026.01.16
- 웹 소켓 통신 구현

2026.01.20
- 그리퍼 가동범위 조정 (0.08 -> 0.06)
- 엔드이펙터 위치 임시 조정 (-0.05)

2026.01.21
- 엔드이펙터 위치 임시 조정 (-0.02)
- 로봇팔 및 오브젝트 마찰력 조정
- 축구공 오브젝트 추가
- 고정 기능을 발판 배치 방식으로 변경

2026.02.03
- 엔드이펙터 시점 카메라 데이터 반환 기능 추가
- 그리퍼 상태(벌어진 정도) 반환 기능 추가
'''

import threading
import pybullet_sim
import flask_server

if __name__ == "__main__":
    server_thread = threading.Thread(target=flask_server.run_flask, daemon=True)
    server_thread.start()

    pybullet_sim.run_simulation()