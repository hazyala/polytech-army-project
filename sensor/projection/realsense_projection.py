"""
Intel RealSense 픽셀→3D 좌표 변환

RealSense SDK의 정확한 역투영 함수를 사용합니다.
"""

import logging
from typing import Tuple


def pixel_to_3d(pixel_x: int, pixel_y: int, depth_m: float, intrinsics) -> Tuple[float, float, float]:
    """
    RealSense 픽셀 좌표를 3D 카메라 좌표(cm)로 변환합니다.
    
    Args:
        pixel_x: 픽셀 X 좌표
        pixel_y: 픽셀 Y 좌표
        depth_m: 실제 깊이 (미터)
        intrinsics: RealSense intrinsics 객체
    
    Returns:
        (x, y, z): 카메라 좌표 cm 단위
    """
    try:
        import pyrealsense2 as rs
        
        # RealSense SDK의 정확한 역투영(Deprojection) 사용
        point_m = rs.rs2_deproject_pixel_to_point(intrinsics, [float(pixel_x), float(pixel_y)], float(depth_m))
        
        # m → cm 변환
        x_cm = point_m[0] * 100
        y_cm = point_m[1] * 100
        z_cm = point_m[2] * 100
        
        logging.debug(f"[RealSenseProjection] 픽셀({pixel_x}, {pixel_y}), depth={depth_m:.4f}m → "
                     f"카메라=({x_cm:.2f}, {y_cm:.2f}, {z_cm:.2f})cm")
        
        return x_cm, y_cm, z_cm
        
    except ImportError:
        logging.error("[RealSenseProjection] pyrealsense2 모듈을 찾을 수 없습니다!")
        return 0.0, 0.0, 0.0
    except Exception as e:
        logging.error(f"[RealSenseProjection] 변환 오류: {e}")
        return 0.0, 0.0, 0.0

def depth_to_point_cloud(depth_image, intrinsics, stride=10):
    """
    Depth 이미지를 3D 포인트 클라우드로 변환합니다.
    성능을 위해 stride 간격으로 샘플링합니다.
    
    Args:
        depth_image: 단위가 미터(m)로 변환된 Depth 이미지 (numpy array)
        intrinsics: 카메라 내인자 객체 또는 딕셔너리
        stride: 픽셀 샘플링 간격 (작을수록 정밀하지만 느림)
        
    Returns:
        points: (N, 3) 형태의 numpy array (cm 단위)
    """
    try:
        import numpy as np
        
        # Intrinsics 파싱
        if isinstance(intrinsics, dict):
            fx, fy = intrinsics['fx'], intrinsics['fy']
            cx, cy = intrinsics['cx'], intrinsics['cy']
        else:
            fx, fy = intrinsics.fx, intrinsics.fy
            cx, cy = intrinsics.ppx, intrinsics.ppy
            
        h, w = depth_image.shape
        
        # 그리드 생성
        u = np.arange(0, w, stride)
        v = np.arange(0, h, stride)
        uu, vv = np.meshgrid(u, v)
        
        # 샘플링된 Depth
        # 유효한 Depth만 추출 (>0)
        z_m = depth_image[vv, uu]
        valid = z_m > 0
        
        z_m = z_m[valid]
        u_valid = uu[valid]
        v_valid = vv[valid]
        
        # 역투영 공식 적용
        x_m = (u_valid - cx) * z_m / fx
        y_m = (v_valid - cy) * z_m / fy
        
        # (N, 3) 배열 생성 및 cm 변환
        points_m = np.stack((x_m, y_m, z_m), axis=-1)
        points_cm = points_m * 100.0
        
        return points_cm
        
    except Exception as e:
        logging.error(f"[RealSenseProjection] 포인트 클라우드 생성 실패: {e}")
        return None

def fit_plane_ransac(points, threshold=1.0, max_iterations=100):
    """
    RANSAC 알고리즘을 사용하여 포인트 클라우드에서 최적의 평면 모델을 추정합니다.
    평면 모델: ax + by + cz + d = 0
    
    Args:
        points: (N, 3) numpy array
        threshold: Inlier 판정 거리 임계값 (cm)
        max_iterations: 반복 횟수
        
    Returns:
        (a, b, c, d): 평면 방정식 계수 (또는 실패 시 None)
        inliers_count: 포함된 점의 개수
    """
    import numpy as np
    
    best_plane = None
    best_inliers_count = -1
    
    n_points = points.shape[0]
    if n_points < 3:
        return None, 0
        
    for _ in range(max_iterations):
        # 3개의 임의 점 선택
        indices = np.random.choice(n_points, 3, replace=False)
        p1, p2, p3 = points[indices]
        
        # 두 벡터 생성
        v1 = p2 - p1
        v2 = p3 - p1
        
        # 법선 벡터 (Cross Product)
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm == 0: continue
        
        a, b, c = normal / norm
        d = -(a*p1[0] + b*p1[1] + c*p1[2])
        
        # 전체 점과의 거리 계산 (점과 평면 사이 거리 공식)
        # dist = |ax + by + cz + d| / sqrt(a^2 + b^2 + c^2)
        # 이미 정규화했으므로 분모는 1
        distances = np.abs(np.dot(points, np.array([a, b, c])) + d)
        
        # Inlier 개수 세기
        n_inliers = np.sum(distances < threshold)
        
        if n_inliers > best_inliers_count:
            best_inliers_count = n_inliers
            best_plane = (a, b, c, d)
            
    return best_plane, best_inliers_count

def calculate_tilt_matrix(accel_x: float, accel_y: float, accel_z: float):
    """
    [IMU Gravity Alignment]
    가속도 센서의 중력 벡터를 이용하여 카메라의 기울기(Pitch, Roll)를 보정하는 회전 행렬을 계산합니다.
    
    원리: 정지 상태에서 가속도 센서는 중력(g) 방향을 가리킵니다.
         이를 [0, 1, 0] (또는 설정에 따라 [0, 0, -1] 등) 벡터와 정렬시킵니다.
    """
    try:
        import numpy as np
        
        # 가속도 벡터 정규화 (Gravity Vector)
        accel = np.array([accel_x, accel_y, accel_z])
        norm = np.linalg.norm(accel)
        if norm == 0: return np.eye(3)
        
        accel_norm = accel / norm
        
        # 목표 수직 벡터 (카메라 좌표계 기준, 보통 Y축이 아래쪽 즉 중력 방향이라고 가정할 때)
        # RealSense D455: Y축이 아래쪽(Down)이므로 중력 가속도는 [0, 1, 0]에 가까워야 함
        target_down = np.array([0, 1, 0])
        
        # 회전축 (Cross Product)
        axis = np.cross(accel_norm, target_down)
        axis_norm = np.linalg.norm(axis)
        
        # 이미 정렬됨
        if axis_norm < 1e-6:
            return np.eye(3)
            
        axis = axis / axis_norm
        
        # 회전각 (Dot Product)
        dot = np.dot(accel_norm, target_down)
        angle = np.arccos(np.clip(dot, -1.0, 1.0))
        
        # 로드리게스 회전 공식 (Rodrigues' Rotation Formula)
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])
        
        R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
        
        return R
        
    except Exception as e:
        logging.error(f"[RealSenseProjection] 틸트 매트릭스 계산 실패: {e}")
        return None

def apply_tilt_correction(x_cm: float, y_cm: float, z_cm: float, tilt_matrix) -> Tuple[float, float, float]:
    """
    계산된 틸트 매트릭스를 3D 점에 적용하여 수직 보정된 좌표를 반환합니다.
    """
    if tilt_matrix is None:
        return x_cm, y_cm, z_cm
        
    try:
        import numpy as np
        point = np.array([x_cm, y_cm, z_cm])
        corrected = tilt_matrix @ point
        return corrected[0], corrected[1], corrected[2]
    except Exception as e:
        return x_cm, y_cm, z_cm

# -----------------------------------------------------------------------------
# 캘리브레이션 시스템 통합
# -----------------------------------------------------------------------------
try:
    from sensor.calibration_system import CameraCalibrator
    from shared.config import GlobalConfig
except ImportError:
    logging.warning("[RealSenseProjection] 캘리브레이션 시스템 모듈을 찾을 수 없습니다.")
    CameraCalibrator = None
    GlobalConfig = None

# 전역 캘리브레이터 인스턴스 (Lazy Initialization & Singleton)
_world_calibrator = None
_gripper_calibrator = None

def _get_calibrator(cal_type: str):
    """캘리브레이터 인스턴스를 반환하거나 생성합니다."""
    global _world_calibrator, _gripper_calibrator
    
    if CameraCalibrator is None: return None
    
    if cal_type == "world":
        if _world_calibrator is None:
            try:
                _world_calibrator = CameraCalibrator(GlobalConfig.CALIBRATION_FILE_WORLD)
                logging.info(f"[RealSenseProjection] 월드 캘리브레이터 로드됨: {GlobalConfig.CALIBRATION_FILE_WORLD}")
            except Exception as e:
                logging.error(f"[RealSenseProjection] 월드 캘리브레이터 초기화 실패: {e}")
        return _world_calibrator
        
    elif cal_type == "gripper":
        if _gripper_calibrator is None:
            try:
                _gripper_calibrator = CameraCalibrator(GlobalConfig.CALIBRATION_FILE_GRIPPER)
                logging.info(f"[RealSenseProjection] 그리퍼 캘리브레이터 로드됨: {GlobalConfig.CALIBRATION_FILE_GRIPPER}")
            except Exception as e:
                logging.error(f"[RealSenseProjection] 그리퍼 캘리브레이터 초기화 실패: {e}")
        return _gripper_calibrator
        
    return None

def camera_to_robot(x: float, y: float, z: float, camera_type: str = "world") -> Tuple[float, float, float]:
    """
    카메라 좌표(cm)를 로봇 베이스 좌표(cm)로 변환합니다.
    캘리브레이션이 로드되어 있으면 변환 행렬을 적용하고, 
    없으면 기존 config.py의 오프셋을 사용합니다.
    
    Args:
        x, y, z: 카메라 좌표계에서의 위치 (cm)
        camera_type: "world" 또는 "gripper"
    
    Returns:
        (rx, ry, rz): 로봇 베이스 좌표계에서의 위치 (cm)
    """
    calibrator = _get_calibrator(camera_type)
    
    # 1. 캘리브레이션 행렬이 있으면 적용
    if calibrator and calibrator.transform_matrix is not None:
         return calibrator.camera_to_robot(x, y, z)
    
    # 2. 없으면 기존 오프셋 방식 적용 (Fallback)
    if camera_type == "world":
         from shared.config import CameraConfig
         offset = CameraConfig.REAL_OFFSET
         # 월드 카메라: 단순히 오프셋을 더하는 방식 (기존 레거시)
         # 주의: 회전을 고려하지 않으므로 부정확할 수 있음
         return x + offset["x"], y + offset["y"], z + offset["z"]
         
    elif camera_type == "gripper":
         # 그리퍼 카메라: 캘리브레이션 없으면 그대로 반환하거나 특정 오프셋 적용
         return x, y, z
         
    return x, y, z
