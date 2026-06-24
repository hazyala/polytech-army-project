"""
실물 로봇 및 RealSense 카메라 연동 테스트 스크립트

이 스크립트는 다음을 검증합니다:
1. RealSense 카메라 프레임 획득 (타임아웃 개선 확인)
2. DOFBOT 로봇 서버 연결
3. 로봇 상태 조회 (position, joints, is_moving)
4. 간단한 움직임 테스트
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

# 설정 확인
from shared.config import GlobalConfig

# 테스트 결과 추적용 변수
camera_ok = False
robot_ok = False


def test_camera():
    """[1단계] RealSense 카메라 프레임 획득 테스트"""
    global camera_ok
    
    print(f"\n{'=' * 60}")
    print("[1단계] RealSense 카메라 프레임 획득 테스트")
    print("=" * 60)

    color, depth = None, None
    
    try:
        from sensor.core import realsense_driver
        
        print("[카메라] 드라이버 시작 중...")
        realsense_driver.start()
        
        print("[카메라] 2초 대기 (프레임 버퍼링)...")
        time.sleep(2.0)
        
        print("[카메라] 프레임 획득 시도...")
        color, depth = realsense_driver.get_frames()
        
        if color is not None and depth is not None:
            print(f"[OK] [카메라] 프레임 획득 성공!")
            print(f"  - Color 프레임 shape: {color.shape}")
            print(f"  - Depth 프레임 shape: {depth.shape}")
            camera_ok = True
        else:
            print(f"[FAIL] [카메라] 프레임 획득 실패")
            
        # IMU 데이터 테스트
        if GlobalConfig.REALSENSE_ENABLE_IMU:
            print("[카메라] IMU 데이터 조회 중...")
            imu_data = realsense_driver.get_imu_data(target='main')
            print(f"[OK] [카메라] IMU 데이터: {imu_data}")
            
    except Exception as e:
        print(f"[FAIL] [카메라] 오류 발생: {e}")
    
    return color, depth


def test_robot():
    """[2단계] DOFBOT 로봇 연결 테스트"""
    global robot_ok
    robot = None
    
    print(f"\n{'=' * 60}")
    print("[2단계] DOFBOT 로봇 연결 테스트")
    print("=" * 60)

    try:
        from embodiment.dofbot_robot import DofbotRobot
        
        print(f"[로봇] {GlobalConfig.DOFBOT_SERVER_URL} 연결 시도...")
        robot = DofbotRobot()
        
        # 연결 대기
        time.sleep(2.0)
        
        if robot.connected:
            print(f"[OK] [로봇] 연결 성공!")
            
            # 로봇 상태 조회
            print("[로봇] 현재 상태 조회 중...")
            pose = robot.get_current_pose()
            
            # 위치 출력
            pos = pose['position']
            print(f"  - EE 위치: x={pos['x']:.2f}, y={pos['y']:.2f}, z={pos['z']:.2f} cm")
            
            # 관절 각도 출력
            joints = pose['joints']
            print(f"  - 관절 각도: {[round(j, 1) for j in joints]}")
            
            # 이동 상태
            print(f"  - 이동 상태: {'이동 중' if pose.get('is_moving', False) else '정지'}")
            
            # TODO: 서버 확장 후 활성화
            # print(f"  - 그리퍼: {pose.get('gripper', 'N/A')}%")
            # orientation = pose.get('orientation')
            # if orientation:
            #     print(f"  - EE 회전: roll={orientation['roll']:.1f}° pitch={orientation['pitch']:.1f}° yaw={orientation['yaw']:.1f}°")
            
            # 간단한 움직임 테스트 (선택적)
            test_motion = input("\n로봇을 간단히 움직여보시겠습니까? (y/n): ").lower().strip()
            
            if test_motion == 'y':
                # TODO: 서버 확장 후 그리퍼 테스트 활성화
                # print("[로봇] 그리퍼 열기...")
                # robot.set_gripper(100)
                # time.sleep(1.0)
                # print("[로봇] 그리퍼 닫기...")
                # robot.set_gripper(0)
                # time.sleep(1.0)
                
                print("[로봇] 관절 기본 자세(90°)로 이동...")
                robot.set_joints([90, 90, 90, 90, 90])
                time.sleep(2.0)
                
                # 이동 후 상태 확인
                pose_after = robot.get_current_pose()
                pos_after = pose_after['position']
                print(f"[OK] [로봇] 움직임 테스트 완료!")
                print(f"  - 이동 후 EE 위치: x={pos_after['x']:.2f}, y={pos_after['y']:.2f}, z={pos_after['z']:.2f} cm")
            else:
                print("[로봇] 움직임 테스트 건너뜀")
            
            robot_ok = True
        else:
            print(f"[FAIL] [로봇] 연결 실패 - 서버가 실행 중인지 확인하세요")
            print(f"    명령: cd 참고/DOFBOT_ROBOT_ARM-main && python main.py")
            
    except Exception as e:
        print(f"[FAIL] [로봇] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    return robot


def print_summary():
    """[3단계] 통합 테스트 요약"""
    print(f"\n{'=' * 60}")
    print("[테스트 요약]")
    print("=" * 60)

    print(f"  - 카메라: {'[OK] 정상' if camera_ok else '[FAIL] 실패'}")
    print(f"  - 로봇: {'[OK] 정상' if robot_ok else '[FAIL] 실패'}")

    if camera_ok and robot_ok:
        print(f"\n[OK] 모든 시스템이 정상 작동합니다!")
        print(f"   main.py를 실행하여 전체 시스템을 시작할 수 있습니다.")
    else:
        print(f"\n[WARNING] 일부 시스템에서 문제가 발생했습니다.")
        if not camera_ok:
            print(f"   - RealSense 카메라가 연결되어 있는지 확인하세요")
        if not robot_ok:
            print(f"   - DOFBOT 서버가 {GlobalConfig.DOFBOT_SERVER_URL}에서 실행 중인지 확인하세요")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("  MACH-VII v2.0 - 실물 로봇 및 카메라 연동 테스트")
    print("=" * 60)

    # 설정 확인
    print(f"\n[설정 확인]")
    print(f"  - SIM_MODE: {GlobalConfig.SIM_MODE}")
    print(f"  - DOFBOT 서버: {GlobalConfig.DOFBOT_SERVER_URL}")
    print(f"  - 프레임 타임아웃: {GlobalConfig.REALSENSE_FRAME_TIMEOUT_MS}ms")
    print(f"  - 최대 재시도: {GlobalConfig.REALSENSE_MAX_TIMEOUT_RETRIES}회")

    # 테스트 실행
    color, depth = test_camera()
    robot = test_robot()
    
    # 결과 요약
    print_summary()

    print(f"\n{'=' * 60}")
    print("테스트 종료")
    print("=" * 60)

    # 정리
    try:
        if robot is not None:
            robot.disconnect()
        # realsense_driver 정리는 모듈 레벨에서 관리
    except Exception:
        pass


if __name__ == "__main__":
    main()
