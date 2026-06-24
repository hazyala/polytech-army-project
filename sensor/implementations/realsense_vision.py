# sensor/realsense_vision.py

import numpy as np
import logging
from ..core import VisionBase
from ..core import realsense_driver

class RealSenseVision(VisionBase):
    """
    [Layer 1: Sensor Implementation] 실물 Intel RealSense 카메라를 위한 구현체입니다.
    
    VisionBase를 상속받아 실제 하드웨어 드라이버(realsense_driver)로부터 데이터를 획득하고,
    베이스 클래스의 필터링된 좌표 변환 로직을 활용합니다.
    """
    def __init__(self):
        """
        하드웨어를 초기화하고 비전 시스템을 시작합니다.
        """
        super().__init__()
        
        # 1. 하드웨어 드라이버 시작 (싱글톤 활용)
        realsense_driver.start()
        
        # 1-2. 그리퍼 카메라 시작 (설정에 따라)
        from shared.config import GlobalConfig
        if GlobalConfig.REALSENSE_ENABLE_GRIPPER_CAM:
            realsense_driver.start_gripper_camera()
            logging.info("[RealSenseVision] 그리퍼 카메라 시작 요청됨")
        
        # 2. 카메라 내인자(Intrinsics: 렌즈 고유의 초점 거리 및 픽셀 중심점 등 카메라 내부 속성) 설정
        # SDK에서 실제 하드웨어 파라미터를 읽어와 베이스 클래스에 등록합니다.
        intr = realsense_driver.get_intrinsics()
        try:
            # 1. 딕셔너리 형태 (더미 모드, 그리퍼 카메라 등)
            self.set_intrinsics(fx=intr["fx"], fy=intr["fy"], cx=intr["cx"], cy=intr["cy"])
        except (TypeError, KeyError):
            # 2. SDK 객체 형태 (pyrealsense2.intrinsics)
            # cx -> ppx, cy -> ppy 이름 다름 주의
            self.set_intrinsics(fx=intr.fx, fy=intr.fy, cx=intr.ppx, cy=intr.ppy)
        
        logging.info(f"[RealSenseVision] 실제 SDK 파라미터 적용 완료: {intr}")
        
        # [Calibration] 바닥 높이 보정값 초기화 (cm)
        self.z_offset_correction = 0.0

    def get_frame(self):
        """
        [VisionBase 인터페이스] 현재 RGB 및 Depth 프레임을 반환합니다.
        
        Returns:
            tuple: (color_frame, depth_frame) 또는 (None, None)
        """
        return realsense_driver.get_frames()

    def get_synced_packet(self):
        """
        RGB, Depth 영상과 해당 시점의 로봇 포즈(Captured Pose)를 하나의 패킷으로 묶어 반환합니다.
        비전-액션 정합(데이터를 시간축에 맞춰 정렬하는 것)을 위해 가장 중요한 메서드입니다.
        """
        color, depth = realsense_driver.get_frames()
        if color is None or depth is None:
            return None
            
        # [Sync] 영상 획득 시점의 로봇 포즈 연동
        # 사용자의 요청대로 SDK(RobotController)로부터 실시간 값을 읽어옵니다.
        # 이를 통해 카메라가 이동(그리퍼 이동)하더라도 정확한 World 좌표를 계산할 수 있습니다.
        pose = self._get_current_robot_pose()
        
        return {
            "color": color,
            "depth": depth,
            "captured_pose": pose
        }

    def _get_tilt_matrix(self):
        """
        [Internal] IMU 데이터로부터 카메라의 기울기 보정 행렬을 계산합니다.
        """
        try:
            # Main 카메라의 IMU 데이터 명시적 요청
            imu_data = realsense_driver.get_imu_data(target='main')
            accel = imu_data.get("accel")
            if accel:
                from sensor.projection import realsense_projection
                return realsense_projection.calculate_tilt_matrix(accel['x'], accel['y'], accel['z'])
        except Exception:
            pass
        return None

    def pixel_to_cm(self, u: int, v: int, depth_m: float):
        """
        [Override] SDK의 공식 역투영 함수 사용 및 IMU 틸트 보정 적용
        """
        if depth_m <= 0:
            return None
            
        # 1. SDK 기반 정밀 역투영 실행
        from sensor.projection import realsense_projection
        # driver에서 intrinsics 객체를 직접 가져옴 (API 변경 반영)
        raw_intr = realsense_driver.intrinsics 
        
        # [Unit Correction] 드라이버의 Depth Scale 적용 (mm -> m)
        scale = realsense_driver.depth_scale if hasattr(realsense_driver, 'depth_scale') else 0.001
        real_depth_meter = depth_m * scale
        
        x, y, z = 0, 0, 0
        if raw_intr is not None:
             x, y, z = realsense_projection.pixel_to_3d(u, v, real_depth_meter, raw_intr)
        else:
             # Fallback (Intrinsics 없을 때)
             # VisionBase의 기본값 사용
             x = (u - self.cx) * real_depth_meter / self.fx
             y = (v - self.cy) * real_depth_meter / self.fy
             z = real_depth_meter * 100 # m to cm

        # 2. [IMU Tilt Correction] 카메라 기울기 보정
        tilt_mat = self._get_tilt_matrix()
        if tilt_mat is not None:
            x, y, z = realsense_projection.apply_tilt_correction(x, y, z, tilt_mat)
            
        # 3. [Floor Level Correction] 바닥 높이 오프셋 적용 (recalibrate_floor 결과)
        z += self.z_offset_correction
             
        # 베이스 클래스의 칼만 필터 적용 및 반환
        return [
            self.filter_x.update(x),
            self.filter_y.update(y),
            self.filter_z.update(z)
        ]

    def pixel_to_local_cm(self, u: int, v: int, depth_m: float):
        """
        [New] 그리퍼 카메라용: 월드 변환 전의 카메라 기준 로컬 좌표(cm)를 반환합니다.
        VisionBridge에서 Dynamic Kinematics를 적용하기 위해 필요합니다.
        """
        if depth_m <= 0: return None

        from sensor.projection import realsense_projection
        raw_intr = realsense_driver.intrinsics
        scale = realsense_driver.depth_scale if hasattr(realsense_driver, 'depth_scale') else 0.001
        real_depth_meter = depth_m * scale
        
        if raw_intr is not None:
            # 1. 픽셀 -> 3D (cm)
            x, y, z = realsense_projection.pixel_to_3d(u, v, real_depth_meter, raw_intr)
            
            # 2. IMU 틸트 보정
            # 그리퍼 카메라도 IMU가 있다면 적용 가능하지만, 현재는 메인 카메라만 적용
            return x, y, z
        else:
            return None

    def recalibrate_floor(self, samples=10) -> float:
        """
        [New] 바닥 평면을 추정하여 카메라의 Z축 높이(Offset)를 보정합니다.
        RANSAC 알고리즘을 사용하여 바닥 평면을 찾고, 예상되는 바닥 높이와의 차이를 계산합니다.
        
        Returns:
            correction_cm: 보정된 높이 오차 (cm)
        """
        logging.info("[RealSenseVision] 바닥 평면 캘리브레이션 시작...")
        sum_correction = 0
        valid_samples = 0
        
        try:
            from sensor.projection import realsense_projection
            
            for _ in range(samples):
                # 최신 프레임 획득
                color, depth = realsense_driver.get_frames()
                if depth is None: continue
                
                # Depth scale 적용
                scale = realsense_driver.depth_scale if hasattr(realsense_driver, 'depth_scale') else 0.001
                depth_meter = depth * scale
                
                # 1. Point Cloud 변환
                intr = realsense_driver.intrinsics
                points = realsense_projection.depth_to_point_cloud(depth_meter, intr, stride=20)
                
                if points is None or len(points) < 100:
                    continue
                    
                # 2. IMU 틸트 보정 적용 (중력 방향 정렬)
                tilt_mat = self._get_tilt_matrix()
                if tilt_mat is not None:
                    # points (N, 3) @ tilt_mat.T (3, 3) -> (N, 3)
                    points = points @ tilt_mat.T
                
                # 3. RANSAC 평면 추정
                # 평면: ax + by + cz + d = 0
                plane, inliers = realsense_projection.fit_plane_ransac(points, threshold=2.0)
                
                if plane:
                    a, b, c, d = plane
                    # 바닥 평면은 보통 Y축(하방) 또는 Z축(전방)과 수직임
                    # 카메라가 아래를 보고 있다면(Top-down), Z값이 바닥 거리임.
                    # 평면의 법선 벡터 (a,b,c)가 [0,0,1]에 가까워야 함.
                    
                    if abs(c) > 0.8: # Z축과 대략 정렬된 경우
                        # d는 원점(카메라)에서 평면까지의 거리 (signed dist)
                        # d = -(ax+by+cz) => 평면의 높이
                        # 카메라가 바닥보다 위에 있으므로, 바닥의 Z좌표는 양수여야 함 (RealSense Z+)
                        floor_dist = abs(d) # cm 단위
                        
                        # 예상되는 바닥 거리와 비교 (예: 설정된 오프셋)
                        # 여기서는 단순히 측정된 바닥 거리를 신뢰하고, 이를 저장할 수도 있음.
                        # 혹은 현재 offset 보정값 계산
                        # TODO: 현재는 단순히 바닥까지의 평균 거리를 로그로 출력하고 반환
                        sum_correction += floor_dist
                        valid_samples += 1
                        
        except Exception as e:
            logging.error(f"[RealSenseVision] 바닥 보정 중 오류: {e}")
            
        if valid_samples > 0:
            avg_floor_dist = sum_correction / valid_samples
            logging.info(f"[RealSenseVision] 측정된 바닥 거리 평균: {avg_floor_dist:.2f} cm")
            # 보정값 업데이트 (이 값을 이용해 pixel_to_cm에서 z값을 조정할 수 있음)
            self.z_offset_correction = avg_floor_dist
            return avg_floor_dist
        else:
            logging.warning("[RealSenseVision] 바닥 평면을 찾지 못했습니다.")
            self.z_offset_correction = 0.0 # 보정 실패 시 초기화
            return 0.0

    def get_gripper_synced_packet(self):
        """
        그리퍼 카메라의 RGB, Depth 영상과 해당 시점의 로봇 포즈를 하나의 패킷으로 묶어 반환합니다.
        """
        color, depth = realsense_driver.get_gripper_frames()
        if color is None or depth is None:
            return None
            
        # 실시간 로봇 포즈 획득 (SDK)
        pose = self._get_current_robot_pose()
        
        return {
            "color": color,
            "depth": depth,
            "captured_pose": pose
        }

    def _get_current_robot_pose(self):
        """
        [Internal] RobotController를 통해 현재 로봇의 엔드 이펙터 위치와 관절 각도를 가져옵니다.
        """
        try:
            # 순환 참조 방지를 위한 지연 import
            from embodiment.robot_controller import robot_controller
            
            # 현재 활성화된 로봇 드라이버(DofbotRobot 등)에서 상태 조회
            robot = robot_controller.robot_driver
            if robot:
                # {position: {x,y,z}, joints: [...]}
                status = robot.get_current_pose()
                
                pos_dict = status.get("position", {"x":0, "y":0, "z":0})
                joints = status.get("joints", [])
                
                # VisionBridge가 기대하는 포맷으로 변환 (pos: list, orn: list)
                # 현재 Dofbot 는 Orientation을 직접 안 줄 수 있으므로, 
                # joints 정보를 포함시켜 추후 FK 계산이 가능하도록 함.
                return {
                    "pos": [pos_dict['x']*0.01, pos_dict['y']*0.01, pos_dict['z']*0.01], # cm -> m 변환 (VisionBridge는 m 단위 pos 기대)
                    "orn": [0, 0, 0, 1], # TODO: FK로 계산 필요. 일단 Identity.
                    "joints": joints
                }
        except Exception as e:
            logging.warning(f"[RealSenseVision] 로봇 포즈 조회 실패: {e}")
            
        return {}

