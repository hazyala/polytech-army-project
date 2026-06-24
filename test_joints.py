"""
DOFBOT 로봇 조인트 각도 테스트 스크립트

현재 조인트 각도를 실시간 조회하고 로봇 상태를 확인합니다.
수동으로 로봇을 움직인 후 Enter를 눌러 상태를 조회할 수 있습니다.
"""

import logging
import time
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

from shared.config import GlobalConfig
from embodiment.dofbot_robot import DofbotRobot


def print_robot_status(pose: dict):
    """로봇 상태를 포맷에 맞춰 출력합니다."""
    print("\n" + "=" * 60)
    
    # EE 위치 (cm)
    pos = pose['position']
    print(f"  EE 위치 (cm):")
    print(f"    x = {pos['x']:>8.2f}")
    print(f"    y = {pos['y']:>8.2f}")
    print(f"    z = {pos['z']:>8.2f}")
    
    # 관절 각도 (도)
    joints = pose['joints']
    print(f"\n  관절 각도 (degrees):")
    for i, angle in enumerate(joints):
        print(f"    Joint {i+1}: {angle:>7.1f}°")
    
    # 관절각 리스트 (복사용)
    print(f"\n  관절각 리스트 (복사용):")
    print(f"    {[round(j, 1) for j in joints]}")
    
    # 이동 상태
    is_moving = pose.get('is_moving', False)
    print(f"\n  이동 상태: {'이동 중' if is_moving else '정지'}")
    
    # TODO: 서버 확장 후 활성화
    # gripper = pose.get('gripper', None)
    # if gripper is not None:
    #     print(f"\n  그리퍼: {gripper:.1f}%")
    # orientation = pose.get('orientation', None)
    # if orientation:
    #     print(f"  EE 회전: roll={orientation['roll']:.1f}° pitch={orientation['pitch']:.1f}° yaw={orientation['yaw']:.1f}°")
    # velocities = pose.get('joint_velocities', None)
    # if velocities:
    #     print(f"  관절 속도 (deg/s): {[round(v, 1) for v in velocities]}")
    
    print("=" * 60)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("  DOFBOT 조인트 각도 테스트")
    print("=" * 60)

    # 로봇 연결
    print(f"\n[로봇] {GlobalConfig.DOFBOT_SERVER_URL} 연결 시도...")
    robot = DofbotRobot()
    time.sleep(2.0)

    if not robot.connected:
        print("[ERROR] 로봇 연결 실패")
        print("DOFBOT 서버가 실행 중인지 확인하세요:")
        print("  cd 참고/DOFBOT_ROBOT_ARM-main && python main.py")
        sys.exit(1)

    print("[OK] 로봇 연결 성공")

    # 현재 상태 조회 루프
    print("\n" + "=" * 60)
    print("현재 로봇 상태 조회 (수동 조작용)")
    print("=" * 60)
    print("\n로봇을 수동으로 움직인 후 Enter를 눌러 현재 상태를 조회하세요.")
    print("종료하려면 'q'를 입력하고 Enter를 누르세요.\n")

    try:
        while True:
            user_input = input("조회하려면 Enter, 종료하려면 'q': ").strip().lower()
            
            if user_input == 'q':
                print("\n프로그램을 종료합니다.")
                break
            
            # 현재 상태 조회 및 출력
            pose = robot.get_current_pose()
            print_robot_status(pose)
            print()
    except KeyboardInterrupt:
        print("\n\n[Ctrl+C] 프로그램을 종료합니다.")
    finally:
        # 정리
        print("\n" + "=" * 60)
        print("테스트 완료")
        print("=" * 60)
        robot.disconnect()


if __name__ == "__main__":
    main()
