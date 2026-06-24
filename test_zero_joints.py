"""
DOFBOT 모든 관절각을 기본 자세(90°)로 설정하는 테스트 스크립트

서보모터 기준 90°가 중립 위치입니다.
이동 후 현재 상태를 확인합니다.
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
    # EE 위치 (cm)
    pos = pose['position']
    print(f"\n  EE 위치 (cm):")
    print(f"    x = {pos['x']:>8.2f}")
    print(f"    y = {pos['y']:>8.2f}")
    print(f"    z = {pos['z']:>8.2f}")
    
    # 관절 각도 (도)
    joints = pose['joints']
    print(f"\n  관절 각도 (degrees):")
    for i, angle in enumerate(joints):
        print(f"    Joint {i+1}: {angle:>7.1f}°")
    
    # 이동 상태
    is_moving = pose.get('is_moving', False)
    print(f"\n  이동 상태: {'이동 중' if is_moving else '정지'}")
    
    # TODO: 서버 확장 후 활성화
    # gripper = pose.get('gripper', None)
    # if gripper is not None:
    #     print(f"  그리퍼: {gripper:.1f}%")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("  DOFBOT 관절각 기본 자세(90°) 설정 테스트")
    print("=" * 60)

    # 로봇 연결
    print(f"\n[로봇] {GlobalConfig.DOFBOT_SERVER_URL} 연결 시도...")
    robot = DofbotRobot()
    time.sleep(2.0)

    if not robot.connected:
        print("[ERROR] 로봇 연결 실패")
        print("DOFBOT 서버가 실행 중인지 확인하세요.")
        sys.exit(1)

    print("[OK] 로봇 연결 성공\n")

    # 이동 전 상태 확인
    print("=" * 60)
    print("[이동 전] 현재 상태")
    print("=" * 60)
    pose_before = robot.get_current_pose()
    print_robot_status(pose_before)

    # 모든 관절각을 기본 자세(90°)로 설정
    zero_joints = [90, 90, 90, 90, 90]
    print(f"\n\n관절각을 기본 자세로 설정합니다: {zero_joints}")
    print("로봇이 이동합니다...\n")

    robot.set_joints(zero_joints)
    time.sleep(3.0)  # 이동 대기

    # 이동 후 결과 확인
    print("=" * 60)
    print("[이동 후] 현재 상태")
    print("=" * 60)
    pose_after = robot.get_current_pose()
    print_robot_status(pose_after)

    # 이동 전후 비교
    print("\n" + "=" * 60)
    print("[비교] 이동 전 → 이동 후")
    print("=" * 60)
    pos_b = pose_before['position']
    pos_a = pose_after['position']
    print(f"  EE 위치 변화: ({pos_b['x']:.2f}, {pos_b['y']:.2f}, {pos_b['z']:.2f})"
          f" → ({pos_a['x']:.2f}, {pos_a['y']:.2f}, {pos_a['z']:.2f})")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

    # 정리
    robot.disconnect()


if __name__ == "__main__":
    main()
