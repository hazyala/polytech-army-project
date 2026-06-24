"""
DOFBOT 로봇 종합 상태 모니터링 테스트 스크립트

목적: DOFBOT 서버로부터 수신되는 모든 실시간 상태를 종합적으로 확인합니다.
기능:
  1. 연결 테스트
  2. 전체 상태 1회 조회
  3. 실시간 모니터링 모드 (0.5초 간격 자동 갱신)
  4. 관절 제어 테스트
"""

import logging
import time
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# 로깅 설정 (WARNING 이상만 출력하여 모니터링 화면을 깔끔하게 유지)
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s:%(name)s:%(message)s'
)

from shared.config import GlobalConfig
from embodiment.dofbot_robot import DofbotRobot


def clear_screen():
    """터미널 화면 클리어"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_status(pose: dict) -> str:
    """로봇 상태를 대시보드 형태의 문자열로 포맷합니다."""
    lines = []
    lines.append("=" * 55)
    lines.append("  DOFBOT 실시간 상태 대시보드")
    lines.append("=" * 55)
    
    # EE 위치 (cm)
    pos = pose.get('position', {})
    lines.append(f"\n  📍 EE 위치 (cm)")
    lines.append(f"     X: {pos.get('x', 0):>8.3f}")
    lines.append(f"     Y: {pos.get('y', 0):>8.3f}")
    lines.append(f"     Z: {pos.get('z', 0):>8.3f}")
    
    # 관절 각도 (도)
    joints = pose.get('joints', [0] * 5)
    lines.append(f"\n  🔧 관절 각도 (degrees)")
    for i, angle in enumerate(joints):
        # 90도 기준으로 편차 표시
        offset = angle - 90.0
        direction = "+" if offset >= 0 else ""
        lines.append(f"     Joint {i+1}: {angle:>7.1f}°  ({direction}{offset:.1f}° from center)")
    
    # 이동 상태
    is_moving = pose.get('is_moving', False)
    status_icon = "🔄" if is_moving else "⏸️"
    status_text = "이동 중" if is_moving else "정지"
    lines.append(f"\n  {status_icon} 이동 상태: {status_text}")
    
    # TODO: 서버 확장 후 활성화
    # gripper = pose.get('gripper', None)
    # if gripper is not None:
    #     grip_bar = "█" * int(gripper / 5) + "░" * (20 - int(gripper / 5))
    #     lines.append(f"\n  🤏 그리퍼: [{grip_bar}] {gripper:.0f}%")
    # 
    # orientation = pose.get('orientation')
    # if orientation:
    #     lines.append(f"\n  🧭 EE 자세 (degrees)")
    #     lines.append(f"     Roll:  {orientation.get('roll', 0):>7.1f}°")
    #     lines.append(f"     Pitch: {orientation.get('pitch', 0):>7.1f}°")
    #     lines.append(f"     Yaw:   {orientation.get('yaw', 0):>7.1f}°")
    # 
    # velocities = pose.get('joint_velocities')
    # if velocities:
    #     lines.append(f"\n  ⚡ 관절 회전율 (deg/s)")
    #     for i, vel in enumerate(velocities):
    #         lines.append(f"     Joint {i+1}: {vel:>7.1f} deg/s")
    
    lines.append("\n" + "=" * 55)
    return "\n".join(lines)


def test_connection(robot: DofbotRobot) -> bool:
    """연결 테스트"""
    print(f"\n[1] 연결 테스트: {GlobalConfig.DOFBOT_SERVER_URL}")
    
    if robot.connected:
        print("    [OK] 연결 성공!")
        return True
    else:
        print("    [FAIL] 연결 실패")
        print("    DOFBOT 서버가 실행 중인지 확인하세요:")
        print("      cd 참고/DOFBOT_ROBOT_ARM-main && python main.py")
        return False


def test_status_query(robot: DofbotRobot):
    """전체 상태 1회 조회"""
    print(f"\n[2] 상태 조회 테스트")
    
    pose = robot.get_current_pose()
    print(format_status(pose))
    
    # 반환된 필드 목록 점검
    print("\n  [필드 점검]")
    expected = ['position', 'joints', 'is_moving']
    for field in expected:
        has_field = field in pose
        print(f"    {field}: {'✅ 있음' if has_field else '❌ 없음'}")
    
    # TODO: 서버 확장 후 점검 항목 추가
    future_fields = ['gripper', 'orientation', 'joint_velocities']
    for field in future_fields:
        has_field = field in pose
        status = '✅ 있음' if has_field else '⏳ 대기 (서버 미지원)'
        print(f"    {field}: {status}")


def monitor_realtime(robot: DofbotRobot, duration: float = 10.0, interval: float = 0.5):
    """실시간 모니터링 모드 (Ctrl+C로 종료)"""
    print(f"\n[3] 실시간 모니터링 ({interval}초 간격)")
    print("    Ctrl+C로 종료합니다.\n")
    time.sleep(1.0)
    
    try:
        start = time.time()
        count = 0
        while True:
            pose = robot.get_current_pose()
            clear_screen()
            
            # 대시보드 출력
            print(format_status(pose))
            
            elapsed = time.time() - start
            count += 1
            print(f"\n  갱신 횟수: {count}  |  경과 시간: {elapsed:.1f}초")
            print("  종료: Ctrl+C")
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n  [모니터링 종료]")


def test_joint_control(robot: DofbotRobot):
    """관절 제어 테스트"""
    print(f"\n[4] 관절 제어 테스트")
    
    user_input = input("    관절 제어 테스트를 수행하시겠습니까? (y/n): ").strip().lower()
    if user_input != 'y':
        print("    건너뜀")
        return
    
    # 현재 상태 저장
    pose_before = robot.get_current_pose()
    print(f"\n    [이동 전] 관절: {[round(j, 1) for j in pose_before['joints']]}")
    
    # 기본 자세로 이동
    target = [90, 90, 90, 90, 90]
    print(f"    [이동 중] 목표 관절: {target}")
    robot.set_joints(target)
    time.sleep(3.0)
    
    # 이동 후 상태 확인
    pose_after = robot.get_current_pose()
    print(f"    [이동 후] 관절: {[round(j, 1) for j in pose_after['joints']]}")
    print("    [OK] 관절 제어 테스트 완료!")


def main():
    """메인 실행 함수"""
    print("=" * 55)
    print("  DOFBOT 종합 상태 모니터링 테스트")
    print("=" * 55)
    print(f"  서버: {GlobalConfig.DOFBOT_SERVER_URL}")
    
    # 로봇 연결
    robot = DofbotRobot()
    time.sleep(2.0)
    
    if not test_connection(robot):
        sys.exit(1)
    
    # 메뉴 루프
    while True:
        print("\n" + "-" * 55)
        print("  [메뉴]")
        print("    1. 상태 1회 조회")
        print("    2. 실시간 모니터링 (Ctrl+C로 복귀)")
        print("    3. 관절 제어 테스트")
        print("    q. 종료")
        print("-" * 55)
        
        choice = input("  선택: ").strip().lower()
        
        if choice == '1':
            test_status_query(robot)
        elif choice == '2':
            monitor_realtime(robot)
        elif choice == '3':
            test_joint_control(robot)
        elif choice == 'q':
            break
        else:
            print("  잘못된 입력입니다.")
    
    # 정리
    print("\n" + "=" * 55)
    print("  테스트 종료")
    print("=" * 55)
    robot.disconnect()


if __name__ == "__main__":
    main()
