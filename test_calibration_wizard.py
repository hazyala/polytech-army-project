"""
MACH VII v2.0 - 통합 캘리브레이션 마법사 (test_calibration_wizard.py)

[목적]
두 대의 RealSense 카메라(메인/그리퍼)와 DOFBOT 로봇이 하나의 좌표계를 공유하도록
Affine 변환 행렬을 수집·계산·저장합니다.

[사용법]
    python test_calibration_wizard.py

[수집 절차]
1. 빨간 마커 위에 로봇 end-effector를 이동합니다.
2. [SPACE] 키를 눌러 현재 포인트를 수집합니다.
   - 메인 카메라와 그리퍼 카메라 양쪽에서 빨간 마커를 검출합니다.
   - 로봇 end-effector XYZ를 동시에 읽습니다.
3. 서로 다른 위치에서 최소 6개 포인트를 수집합니다.
4. [S] 키로 행렬 계산 및 JSON 저장합니다.
5. [Q] 키로 종료합니다.

[키 바인딩]
    SPACE : 현재 위치 포인트 수집
    R     : 마지막 포인트 삭제
    C     : 전체 포인트 초기화
    S     : 계산 및 저장
    Q     : 종료
"""

import sys
import os
import time
import logging
import cv2
import numpy as np
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def print_header():
    """헤더 출력"""
    print("=" * 65)
    print("   MACH VII v2.0 - 통합 캘리브레이션 마법사")
    print("=" * 65)
    print("  목적: 두 RealSense 카메라 + DOFBOT 로봇 하나의 좌표계 통합")
    print()
    print("  [키 바인딩]")
    print("    SPACE : 현재 포인트 수집")
    print("    R     : 마지막 포인트 삭제")
    print("    C     : 전체 포인트 초기화")
    print("    S     : 계산 및 저장")
    print("    Q     : 종료")
    print("=" * 65)


def get_robot_ee_position(robot):
    """
    DOFBOT 로봇에서 현재 end-effector XYZ 좌표(cm)를 읽어옵니다.

    Returns:
        (x, y, z) 튜플(cm) 또는 None
    """
    try:
        status = robot.get_current_pose()
        pos = status.get("position", {})
        x = float(pos.get("x", 0.0))
        y = float(pos.get("y", 0.0))
        z_val = float(pos.get("z", 0.0))
        return (x, y, z_val)
    except Exception as e:
        logger.error(f"[Robot] end-effector 위치 조회 실패: {e}")
        return None


def pixel_to_camera_3d(u, v, depth_raw, intrinsics, depth_scale):
    """
    픽셀 좌표 + raw depth → 카메라 좌표계 3D 점(cm)으로 변환합니다.

    Args:
        u, v       : 픽셀 좌표
        depth_raw  : 해당 픽셀의 raw depth 값 (uint16, mm 단위)
        intrinsics : RealSense intrinsics 객체
        depth_scale: 드라이버의 depth scale (m/unit)

    Returns:
        (x, y, z) cm 단위 또는 None
    """
    if depth_raw <= 0:
        return None
    try:
        import pyrealsense2 as rs
        depth_m = depth_raw * depth_scale
        point_m = rs.rs2_deproject_pixel_to_point(
            intrinsics, [float(u), float(v)], float(depth_m)
        )
        # m → cm 변환
        return (point_m[0] * 100.0, point_m[1] * 100.0, point_m[2] * 100.0)
    except Exception as e:
        logger.error(f"[Projection] 픽셀→3D 변환 실패: {e}")
        return None


def collect_point_from_frame(
    color_frame, depth_frame, intrinsics, depth_scale, detector
):
    """
    단일 프레임에서 빨간 마커를 검출하고 카메라 좌표를 반환합니다.

    Returns:
        ((u, v), camera_xyz_cm, vis_frame) 또는 (None, None, vis_frame)
    """
    result, confidence = detector.detect_with_score(color_frame, depth_frame)
    vis = color_frame.copy()

    if result is None:
        cv2.putText(vis, "No red marker detected!", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return None, None, vis

    u, v, depth_m_from_avg = result

    # 신뢰도 표시
    conf_color = (0, 255, 0) if confidence > 0.5 else (0, 165, 255)
    vis = detector.draw_detection(vis, result)
    cv2.putText(vis, f"Conf: {confidence:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, conf_color, 2)

    # 정밀 depth: depth_frame에서 직접 읽기 (u,v 주변 5×5 평균)
    half = 2
    h, w = depth_frame.shape
    region = depth_frame[
        max(0, v - half): min(h, v + half + 1),
        max(0, u - half): min(w, u + half + 1)
    ]
    valid = region[region > 0]
    if len(valid) == 0:
        return None, None, vis

    depth_raw = float(np.median(valid))
    cam_xyz = pixel_to_camera_3d(u, v, depth_raw, intrinsics, depth_scale)

    return (u, v), cam_xyz, vis


def build_overlay(vis_world, vis_gripper,
                  n_world, n_gripper, n_robot,
                  target_n=6):
    """
    메인/그리퍼 카메라 프레임을 좌우로 합치고 수집 현황을 오버레이합니다.
    """
    # 그리퍼 프레임이 없으면 빈 검정 이미지로 대체
    if vis_gripper is None:
        h = vis_world.shape[0]
        vis_gripper = np.zeros((h, vis_world.shape[1], 3), dtype=np.uint8)
        cv2.putText(vis_gripper, "Gripper Camera: N/A", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)

    # 크기 통일 (세로 기준)
    h_target = max(vis_world.shape[0], vis_gripper.shape[0])
    w_world  = int(vis_world.shape[1] * h_target / vis_world.shape[0])
    w_grip   = int(vis_gripper.shape[1] * h_target / vis_gripper.shape[0])
    vis_world   = cv2.resize(vis_world,   (w_world, h_target))
    vis_gripper = cv2.resize(vis_gripper, (w_grip,  h_target))

    combined = np.hstack([vis_world, vis_gripper])

    # 라벨
    cv2.putText(combined, "Main Camera", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.putText(combined, "Gripper Camera", (w_world + 10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # 수집 현황
    info = (f"World pts: {n_world} | Gripper pts: {n_gripper} | "
            f"Robot pts: {n_robot} | Target: {target_n}")
    cv2.putText(combined, info, (10, h_target - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 키 가이드
    guide = "SPACE:Capture  R:Remove  C:Clear  S:Save  Q:Quit"
    cv2.putText(combined, guide, (10, h_target - 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    return combined


def run_calibration_wizard():
    """캘리브레이션 마법사 메인 루프"""
    print_header()

    # ──────────────────────────────────────────────────
    # 1. 의존 모듈 초기화
    # ──────────────────────────────────────────────────
    from shared.config import GlobalConfig, CalibrationConfig
    from sensor.core.realsense_driver import realsense_driver
    from sensor.calibration_system import RedTapeDetector, MultiCameraCalibrator

    # 캘리브레이터
    mcc = MultiCameraCalibrator()
    detector = RedTapeDetector()

    # 포인트 수집 버퍼 (UI 표시용)
    collected_points = []  # [(world_cam, gripper_cam, robot)]

    # ──────────────────────────────────────────────────
    # 2. RealSense 드라이버 시작
    # ──────────────────────────────────────────────────
    print("\n[1단계] RealSense 드라이버 시작...")
    realsense_driver.start()

    if GlobalConfig.REALSENSE_ENABLE_GRIPPER_CAM:
        realsense_driver.start_gripper_camera()
        print("       그리퍼 카메라 시작 완료")

    print("       카메라 워밍업 대기 (2초)...")
    time.sleep(2.0)

    if realsense_driver.intrinsics is None:
        logger.error("메인 카메라 Intrinsics 없음. RealSense 연결을 확인하세요.")
        realsense_driver.stop()
        return

    main_intrinsics  = realsense_driver.intrinsics
    main_depth_scale = realsense_driver.depth_scale

    grip_intrinsics  = getattr(realsense_driver, 'gripper_raw_intrinsics', None)
    grip_depth_scale = getattr(realsense_driver, 'gripper_depth_scale', 0.001)

    print(f"       메인 카메라 Intrinsics: fx={main_intrinsics.fx:.1f}, fy={main_intrinsics.fy:.1f}")
    if grip_intrinsics:
        print(f"       그리퍼 카메라 Intrinsics: fx={grip_intrinsics.fx:.1f}, fy={grip_intrinsics.fy:.1f}")
    else:
        print("       그리퍼 카메라: 미연결 (선택 사항)")

    # ──────────────────────────────────────────────────
    # 3. DOFBOT 로봇 연결
    # ──────────────────────────────────────────────────
    print("\n[2단계] DOFBOT 로봇 연결 중...")
    robot = None
    try:
        from embodiment.dofbot_robot import DofbotRobot
        robot = DofbotRobot()
        time.sleep(1.5)
        if robot.connected:
            print(f"       연결 성공: {GlobalConfig.DOFBOT_SERVER_URL}")
            pose = robot.get_current_pose()
            pos = pose.get("position", {})
            print(f"       현재 EE 위치: x={pos.get('x',0):.2f}, y={pos.get('y',0):.2f}, z={pos.get('z',0):.2f} cm")
        else:
            print("       [경고] 로봇 연결 실패. 로봇 좌표 없이 카메라 좌표만 수집합니다.")
            robot = None
    except Exception as e:
        print(f"       [경고] 로봇 연결 오류: {e}")
        robot = None

    # ──────────────────────────────────────────────────
    # 4. 기존 캘리브레이션 포인트 표시
    # ──────────────────────────────────────────────────
    status = mcc.get_status()
    print(f"\n[기존 캘리브레이션 상태]")
    print(f"  메인 카메라: {'완료' if status['world']['calibrated'] else '미완료'} | "
          f"포인트: {status['world']['num_points']}개")
    print(f"  그리퍼 카메라: {'완료' if status['gripper']['calibrated'] else '미완료'} | "
          f"포인트: {status['gripper']['num_points']}개")

    target_n = CalibrationConfig.MIN_CALIBRATION_POINTS
    print(f"\n  최소 필요 포인트: {target_n}개 (서로 다른 위치에서 수집)")
    print("\n[준비 완료] 창에서 SPACE 키를 눌러 포인트를 수집하세요.")

    # ──────────────────────────────────────────────────
    # 5. 메인 루프 (OpenCV 윈도우)
    # ──────────────────────────────────────────────────
    WINDOW_TITLE = "Calibration Wizard - MACH VII"
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, 1280, 480)

    while True:
        # 프레임 획득
        color_main,  depth_main  = realsense_driver.get_frames()
        color_grip,  depth_grip  = realsense_driver.get_gripper_frames()

        if color_main is None:
            # 프레임 미도착 시 짧게 대기
            time.sleep(0.05)
            continue

        # 메인 카메라 마커 검출 및 시각화
        _, _, vis_world = collect_point_from_frame(
            color_main, depth_main, main_intrinsics, main_depth_scale, detector
        )

        # 그리퍼 카메라 마커 검출 및 시각화
        vis_gripper = None
        if color_grip is not None and grip_intrinsics is not None:
            _, _, vis_gripper = collect_point_from_frame(
                color_grip, depth_grip, grip_intrinsics, grip_depth_scale, detector
            )

        # 수집된 포인트 수 표시
        n_world  = len(mcc.world_calibrator.points)
        n_gripper = len(mcc.gripper_calibrator.points)
        n_robot  = len(collected_points)

        # 컬러 상태 표시: 포인트가 충분하면 녹색, 부족하면 주황
        progress_color = (0, 255, 0) if n_world >= target_n else (0, 165, 255)
        cv2.putText(vis_world,
                    f"Points: {n_world}/{target_n}",
                    (10, vis_world.shape[0] - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, progress_color, 2)

        # 통합 디스플레이
        combined = build_overlay(vis_world, vis_gripper,
                                 n_world, n_gripper, n_robot, target_n)
        cv2.imshow(WINDOW_TITLE, combined)

        key = cv2.waitKey(30) & 0xFF

        # ─── SPACE: 포인트 수집 ───────────────────────
        if key == ord(' '):
            print("\n[SPACE] 포인트 수집 중...")

            # 메인 카메라
            main_uv, main_cam_xyz, _ = collect_point_from_frame(
                color_main, depth_main, main_intrinsics, main_depth_scale, detector
            )

            # 그리퍼 카메라
            grip_uv, grip_cam_xyz = None, None
            if color_grip is not None and grip_intrinsics is not None:
                grip_uv, grip_cam_xyz, _ = collect_point_from_frame(
                    color_grip, depth_grip, grip_intrinsics, grip_depth_scale, detector
                )

            # 로봇 EE 위치
            robot_xyz = None
            if robot:
                robot_xyz = get_robot_ee_position(robot)

            # 유효성 검사
            if main_cam_xyz is None:
                print("  [실패] 메인 카메라에서 빨간 마커를 검출하지 못했습니다.")
                continue

            if robot_xyz is None:
                print("  [경고] 로봇 좌표를 수집할 수 없습니다.")
                print("         수동으로 로봇 좌표를 입력하세요 (형식: x,y,z 또는 skip):")
                user_input = input("         > ").strip()
                if user_input.lower() == "skip":
                    print("  [건너뜀] 이 포인트를 건너뜁니다.")
                    continue
                try:
                    parts = [float(v) for v in user_input.split(",")]
                    if len(parts) == 3:
                        robot_xyz = tuple(parts)
                    else:
                        print("  [오류] 잘못된 형식. 포인트를 건너뜁니다.")
                        continue
                except ValueError:
                    print("  [오류] 숫자 파싱 실패. 포인트를 건너뜁니다.")
                    continue

            # 캘리브레이터에 포인트 추가
            mcc.add_world_point(robot_xyz, main_cam_xyz)

            if grip_cam_xyz:
                mcc.add_gripper_point(robot_xyz, grip_cam_xyz)
                print(f"  [수집 완료] Robot=({robot_xyz[0]:.2f}, {robot_xyz[1]:.2f}, {robot_xyz[2]:.2f}) cm")
                print(f"              메인 카메라=({main_cam_xyz[0]:.2f}, {main_cam_xyz[1]:.2f}, {main_cam_xyz[2]:.2f}) cm")
                print(f"              그리퍼 카메라=({grip_cam_xyz[0]:.2f}, {grip_cam_xyz[1]:.2f}, {grip_cam_xyz[2]:.2f}) cm")
            else:
                print(f"  [수집 완료] Robot=({robot_xyz[0]:.2f}, {robot_xyz[1]:.2f}, {robot_xyz[2]:.2f}) cm")
                print(f"              메인 카메라=({main_cam_xyz[0]:.2f}, {main_cam_xyz[1]:.2f}, {main_cam_xyz[2]:.2f}) cm")
                print(f"              그리퍼 카메라: 검출 실패 (포인트 미추가)")

            collected_points.append((main_cam_xyz, grip_cam_xyz, robot_xyz))
            print(f"  총 포인트: 메인={len(mcc.world_calibrator.points)}, "
                  f"그리퍼={len(mcc.gripper_calibrator.points)}")

        # ─── R: 마지막 포인트 삭제 ────────────────────
        elif key == ord('r') or key == ord('R'):
            mcc.remove_last_world_point()
            mcc.remove_last_gripper_point()
            if collected_points:
                collected_points.pop()
            print(f"[R] 마지막 포인트 삭제. 현재 메인={len(mcc.world_calibrator.points)}개")

        # ─── C: 전체 초기화 ───────────────────────────
        elif key == ord('c') or key == ord('C'):
            mcc.clear_all()
            collected_points.clear()
            print("[C] 전체 포인트 초기화 완료")

        # ─── S: 계산 및 저장 ──────────────────────────
        elif key == ord('s') or key == ord('S'):
            print("\n[S] 캘리브레이션 행렬 계산 중...")
            n_world_pts = len(mcc.world_calibrator.points)

            if n_world_pts < 4:
                print(f"  [실패] 포인트 부족: {n_world_pts}개 (최소 4개 필요)")
                continue

            results = mcc.calculate_all()

            print("\n[결과 요약]")
            max_err = CalibrationConfig.MAX_REPROJECTION_ERROR_CM
            for cam_name, key_name in [("메인(월드) 카메라", "world"), ("그리퍼 카메라", "gripper")]:
                ok = results.get(key_name, False)
                if ok:
                    calibrator = (mcc.world_calibrator
                                  if key_name == "world"
                                  else mcc.gripper_calibrator)
                    err = calibrator.reprojection_error or 0.0
                    valid = calibrator.is_calibration_valid()
                    status_str = "✅ 합격" if valid else "⚠️ 오차 초과"
                    print(f"  {cam_name}: {status_str} | 재투영 오차: {err:.2f} cm (기준: {max_err:.1f} cm)")
                else:
                    pts = (len(mcc.world_calibrator.points)
                           if key_name == "world"
                           else len(mcc.gripper_calibrator.points))
                    print(f"  {cam_name}: ❌ 실패 (포인트: {pts}개)")

            # 메인 캘리브레이션 성공 시 저장
            if results.get("world"):
                mcc.save_all()
                print("\n  JSON 저장 완료!")
                print(f"  - 메인: {GlobalConfig.CALIBRATION_FILE_WORLD}")
                print(f"  - 그리퍼: {GlobalConfig.CALIBRATION_FILE_GRIPPER}")

                # 로봇 베이스 좌표 검증 (테이프 마커 기준)
                print("\n[검증] 수집된 포인트의 예측 좌표를 확인합니다:")
                for i, (wcam, gcam, robot) in enumerate(collected_points[:3]):
                    pred = mcc.world_to_robot(wcam[0], wcam[1], wcam[2])
                    err_vec = (pred[0]-robot[0], pred[1]-robot[1], pred[2]-robot[2])
                    err_dist = (err_vec[0]**2 + err_vec[1]**2 + err_vec[2]**2) ** 0.5
                    print(f"  포인트 {i+1}: 실제=({robot[0]:.2f},{robot[1]:.2f},{robot[2]:.2f})"
                          f" 예측=({pred[0]:.2f},{pred[1]:.2f},{pred[2]:.2f})"
                          f" 오차={err_dist:.2f}cm")
            else:
                print("\n  [주의] 메인 카메라 캘리브레이션이 실패하여 저장하지 않았습니다.")

        # ─── Q: 종료 ──────────────────────────────────
        elif key == ord('q') or key == ord('Q') or key == 27:
            print("\n[Q] 캘리브레이션 마법사 종료")
            break

    cv2.destroyAllWindows()
    realsense_driver.stop()
    if robot:
        try:
            robot.disconnect()
        except Exception:
            pass

    print("\n✅ 마법사 종료. 저장된 파일을 사용하여 시스템을 재시작하면 캘리브레이션이 자동 적용됩니다.")


if __name__ == "__main__":
    run_calibration_wizard()
