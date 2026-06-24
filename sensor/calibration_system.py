import cv2
import numpy as np
import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict

@dataclass
class CalibrationPoint:
    """단일 캘리브레이션 포인트: 로봇 좌표 ↔ 카메라 좌표 대응쌍"""
    robot_x: float  # 로봇 베이스 기준 X (cm)
    robot_y: float  # 로봇 베이스 기준 Y (cm)
    robot_z: float  # 로봇 베이스 기준 Z (cm)
    camera_x: float  # 카메라 좌표계 X (cm)
    camera_y: float  # 카메라 좌표계 Y (cm)
    camera_z: float  # 카메라 좌표계 Z (cm)


class RedTapeDetector:
    """
    [Vision] 빨간색 테이프 마커를 검출하여 이미지 상의 중심점(u, v)을 반환합니다.
    HSV 색상 공간을 사용하여 빨간색 범위를 필터링합니다.
    CalibrationConfig의 HSV 파라미터를 우선 사용하고, 없으면 기본값을 사용합니다.
    """
    def __init__(self):
        # CalibrationConfig에서 HSV 파라미터 로드 (없으면 기본값 사용)
        try:
            from shared.config import CalibrationConfig
            self.lower_red1 = np.array(CalibrationConfig.RED_HSV_LOWER1, dtype=np.uint8)
            self.upper_red1 = np.array(CalibrationConfig.RED_HSV_UPPER1, dtype=np.uint8)
            self.lower_red2 = np.array(CalibrationConfig.RED_HSV_LOWER2, dtype=np.uint8)
            self.upper_red2 = np.array(CalibrationConfig.RED_HSV_UPPER2, dtype=np.uint8)
            self.min_area   = CalibrationConfig.RED_MIN_AREA
        except (ImportError, AttributeError):
            # 빨간색은 HSV에서 0~10, 170~180 두 구간에 걸쳐 있음
            self.lower_red1 = np.array([0,   120,  70], dtype=np.uint8)
            self.upper_red1 = np.array([10,  255, 255], dtype=np.uint8)
            self.lower_red2 = np.array([170, 120,  70], dtype=np.uint8)
            self.upper_red2 = np.array([180, 255, 255], dtype=np.uint8)
            self.min_area   = 200

    def detect(self, color_frame: np.ndarray, depth_frame: np.ndarray = None) -> Optional[Tuple[int, int, float]]:
        """
        이미지에서 가장 큰 빨간색 영역의 중심점(u, v)과 해당 지점의 depth(m)를 반환합니다.

        Returns:
            (u, v, depth_m) 튜플. 검출 실패 시 None 반환.
        """
        if color_frame is None:
            return None

        hsv = cv2.cvtColor(color_frame, cv2.COLOR_BGR2HSV)

        # 두 범위의 마스크 생성 및 합치기
        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        # 노이즈 제거 (Opening → Closing)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 윤곽선 검출
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # 가장 큰 윤곽선 선택
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)

        # 최소 면적 기준 미달 시 무시
        if area < self.min_area:
            return None

        # 중심점 계산 (모멘트)
        M = cv2.moments(largest_contour)
        if M["m00"] == 0:
            return None

        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])

        # Depth 값 추출 (depth_frame이 제공된 경우)
        depth_val = 0.0
        if depth_frame is not None:
            # 주변 픽셀 평균으로 안정화 (5×5 커널)
            depth_val = self._get_average_depth(depth_frame, cX, cY, kernel_size=5)

        return cX, cY, depth_val

    def detect_with_score(self, color_frame: np.ndarray, depth_frame: np.ndarray = None):
        """
        detect()와 동일하되, 검출 신뢰도(면적 기반 점수 0~1)도 함께 반환합니다.

        Returns:
            ((u, v, depth_m), confidence) 또는 (None, 0.0)
        """
        if color_frame is None:
            return None, 0.0

        hsv = cv2.cvtColor(color_frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0.0

        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        if area < self.min_area:
            return None, 0.0

        M = cv2.moments(largest_contour)
        if M["m00"] == 0:
            return None, 0.0

        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])

        depth_val = 0.0
        if depth_frame is not None:
            depth_val = self._get_average_depth(depth_frame, cX, cY, kernel_size=5)

        # 신뢰도: 면적을 기준으로 정규화 (1000픽셀을 1.0으로 간주, 최대 1.0)
        confidence = min(area / 1000.0, 1.0)

        return (cX, cY, depth_val), confidence

    def draw_detection(self, frame: np.ndarray, detection_result) -> np.ndarray:
        """
        검출 결과를 프레임에 시각화하여 반환합니다.
        중심점(+), 원, 좌표 텍스트를 오버레이합니다.
        """
        if frame is None or detection_result is None:
            return frame

        cX, cY, depth_val = detection_result
        vis = frame.copy()

        # 중심점 원 및 크로스헤어
        cv2.circle(vis, (cX, cY), 10, (0, 255, 0), 2)
        cv2.line(vis, (cX - 15, cY), (cX + 15, cY), (0, 255, 0), 2)
        cv2.line(vis, (cX, cY - 15), (cX, cY + 15), (0, 255, 0), 2)

        # 좌표 텍스트
        label = f"({cX},{cY}) d={depth_val:.3f}m"
        cv2.putText(vis, label, (cX + 15, cY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        return vis

    def _get_average_depth(self, depth_frame, u, v, kernel_size=5):
        """주변 픽셀의 깊이 평균을 구합니다 (0인 값 제외)"""
        h, w = depth_frame.shape
        half = kernel_size // 2

        valid_depths = []
        for y in range(max(0, v - half), min(h, v + half + 1)):
            for x in range(max(0, u - half), min(w, u + half + 1)):
                d = depth_frame[y, x]
                if d > 0:
                    valid_depths.append(d)

        if not valid_depths:
            return 0.0

        # 미터 단위 변환 (RealSense depth_frame은 uint16 mm 단위)
        return (sum(valid_depths) / len(valid_depths)) * 0.001


class CameraCalibrator:
    """
    [System] 단일 카메라-로봇 간 좌표 변환 시스템.
    Affine 변환 행렬을 사용하여 3D 카메라 좌표를 3D 로봇 좌표로 변환합니다.
    """
    def __init__(self, calibration_file: Path):
        self.calibration_file = calibration_file
        self.points: List[CalibrationPoint] = []
        self.transform_matrix = None  # 4x4 행렬
        self.reprojection_error = None  # 마지막 계산된 재투영 오차 (cm)
        self.load_calibration()

    def add_point(self, robot_pos: Tuple[float, float, float], camera_pos: Tuple[float, float, float]):
        """캘리브레이션 포인트 추가"""
        point = CalibrationPoint(
            robot_x=robot_pos[0], robot_y=robot_pos[1], robot_z=robot_pos[2],
            camera_x=camera_pos[0], camera_y=camera_pos[1], camera_z=camera_pos[2]
        )
        self.points.append(point)
        logging.info(f"[Calibration] 포인트 추가: Robot{robot_pos} <-> Camera{camera_pos} (총 {len(self.points)}개)")

    def clear_points(self):
        """수집된 포인트 전체 초기화"""
        self.points = []
        self.reprojection_error = None
        logging.info("[Calibration] 포인트 전체 초기화됨")

    def remove_last_point(self):
        """마지막으로 추가된 포인트 삭제"""
        if self.points:
            removed = self.points.pop()
            logging.info(f"[Calibration] 마지막 포인트 삭제: Robot({removed.robot_x:.2f}, {removed.robot_y:.2f}, {removed.robot_z:.2f})")

    def calculate_transform(self) -> bool:
        """
        수집된 포인트들을 사용하여 최적의 Affine 변환 행렬을 계산합니다.
        최소 4개 이상의 포인트가 필요합니다 (6개 이상 권장).
        """
        if len(self.points) < 4:
            logging.error(f"[Calibration] 포인트 부족. 최소 4개 필요 (현재: {len(self.points)})")
            return False

        try:
            # 입력 (Camera) -> 출력 (Robot)
            src_pts = np.array([[p.camera_x, p.camera_y, p.camera_z] for p in self.points], dtype=np.float64)
            dst_pts = np.array([[p.robot_x,  p.robot_y,  p.robot_z]  for p in self.points], dtype=np.float64)

            # Affine 3D 변환 행렬 계산 (OpenCV estimateAffine3D - RANSAC 내장)
            # retval: 성공 여부, matrix: 3x4 행렬, inliers
            retval, matrix, inliers = cv2.estimateAffine3D(src_pts, dst_pts, confidence=0.999)

            if not retval:
                logging.error("[Calibration] 변환 행렬 계산 실패 (RANSAC 수렴 안됨)")
                return False

            # 4x4 Homogeneous 행렬로 확장
            self.transform_matrix = np.eye(4)
            self.transform_matrix[:3, :] = matrix

            # 재투영 오차 계산
            self.reprojection_error = self._compute_reprojection_error(src_pts, dst_pts)

            inlier_count = int(inliers.sum()) if inliers is not None else len(self.points)
            logging.info(f"[Calibration] 변환 행렬 계산 성공 | Inliers: {inlier_count}/{len(self.points)} | 재투영 오차: {self.reprojection_error:.2f} cm")
            logging.info(f"\n{self.transform_matrix}")
            return True

        except Exception as e:
            logging.error(f"[Calibration] 계산 중 오류 발생: {e}")
            return False

    def _compute_reprojection_error(self, src_pts: np.ndarray, dst_pts: np.ndarray) -> float:
        """
        변환 행렬을 적용하여 예측된 좌표와 실제 로봇 좌표의 평균 오차(cm)를 계산합니다.

        Args:
            src_pts: 카메라 좌표 배열 (N, 3)
            dst_pts: 로봇 좌표 배열 (N, 3)

        Returns:
            평균 오차 (cm)
        """
        if self.transform_matrix is None:
            return float('inf')

        errors = []
        for cam_pt, robot_pt in zip(src_pts, dst_pts):
            predicted = self.camera_to_robot(cam_pt[0], cam_pt[1], cam_pt[2])
            error = np.linalg.norm(np.array(predicted) - robot_pt)
            errors.append(error)

        return float(np.mean(errors)) if errors else float('inf')

    def get_reprojection_error(self) -> Optional[float]:
        """마지막으로 계산된 재투영 오차(cm)를 반환합니다. 계산 전이면 None."""
        return self.reprojection_error

    def is_calibration_valid(self) -> bool:
        """
        캘리브레이션이 유효한지 확인합니다.
        행렬이 존재하고 재투영 오차가 허용 범위 내의 있어야 합니다.
        """
        if self.transform_matrix is None:
            return False
        try:
            from shared.config import CalibrationConfig
            max_err = CalibrationConfig.MAX_REPROJECTION_ERROR_CM
        except (ImportError, AttributeError):
            max_err = 5.0

        if self.reprojection_error is None:
            return True  # 저장된 캘리브레이션 파일을 로드한 경우 (오차 없음)
        return self.reprojection_error <= max_err

    def save_calibration(self):
        """캘리브레이션 결과를 JSON 파일로 저장"""
        if self.transform_matrix is None:
            logging.warning("[Calibration] 저장할 변환 행렬이 없습니다.")
            return

        data = {
            "transform_matrix": self.transform_matrix.tolist(),
            "points": [asdict(p) for p in self.points],
            "reprojection_error_cm": self.reprojection_error,
            "num_points": len(self.points),
            "timestamp": cv2.getTickCount()
        }

        try:
            self.calibration_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=4)
            logging.info(f"[Calibration] 저장 완료: {self.calibration_file} (오차: {self.reprojection_error:.2f} cm)")
        except Exception as e:
            logging.error(f"[Calibration] 저장 실패: {e}")

    def load_calibration(self):
        """캘리브레이션 파일 로드"""
        if not self.calibration_file.exists():
            logging.warning(f"[Calibration] 파일 없음 (미캘리브레이션 상태): {self.calibration_file}")
            return

        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)

            matrix = np.array(data["transform_matrix"])
            if matrix.shape == (4, 4):
                self.transform_matrix = matrix
                # 포인트 데이터 (선택적 로드)
                if "points" in data:
                    self.points = [CalibrationPoint(**p) for p in data["points"]]
                # 저장된 재투영 오차 복원
                self.reprojection_error = data.get("reprojection_error_cm", None)
                err_str = f"{self.reprojection_error:.2f} cm" if self.reprojection_error else "알 수 없음"
                logging.info(f"[Calibration] 로드 완료: {self.calibration_file} | 포인트: {len(self.points)}개 | 오차: {err_str}")
            else:
                logging.error(f"[Calibration] 잘못된 행렬 형상: {matrix.shape}")

        except Exception as e:
            logging.error(f"[Calibration] 로드 실패: {e}")

    def camera_to_robot(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        카메라 좌표(cm)를 로봇 좌표(cm)로 변환합니다.
        캘리브레이션 행렬이 없으면 원본 좌표를 그대로 반환합니다.
        """
        if self.transform_matrix is None:
            return x, y, z

        # Homogeneous 좌표로 변환 후 4x4 행렬 적용
        vec = np.array([x, y, z, 1.0])
        transformed = self.transform_matrix @ vec

        return float(transformed[0]), float(transformed[1]), float(transformed[2])


class MultiCameraCalibrator:
    """
    [System] 두 대의 RealSense 카메라(메인/그리퍼)와 로봇을 하나의 좌표계로 통합 관리하는 캘리브레이터.

    각 카메라별로 독립적인 CameraCalibrator 인스턴스를 유지하며,
    두 카메라→로봇 변환 행렬을 각각 계산·저장합니다.

    사용법:
        mcc = MultiCameraCalibrator()
        mcc.add_world_point(robot_pos, world_cam_pos)    # 메인 카메라 포인트 추가
        mcc.add_gripper_point(robot_pos, gripper_cam_pos) # 그리퍼 카메라 포인트 추가
        mcc.calculate_all()                              # 두 행렬 동시 계산
        mcc.save_all()                                   # 두 결과 저장
        robot_pos = mcc.world_to_robot(cx, cy, cz)      # 메인→로봇 변환
        robot_pos = mcc.gripper_to_robot(cx, cy, cz)   # 그리퍼→로봇 변환
    """
    def __init__(self):
        from shared.config import GlobalConfig
        # 메인(월드) 카메라 캘리브레이터
        self.world_calibrator   = CameraCalibrator(GlobalConfig.CALIBRATION_FILE_WORLD)
        # 그리퍼 카메라 캘리브레이터
        self.gripper_calibrator = CameraCalibrator(GlobalConfig.CALIBRATION_FILE_GRIPPER)

    # ─── 포인트 추가 ────────────────────────────────────────────────────────
    def add_world_point(self, robot_pos: Tuple[float, float, float],
                        world_cam_pos: Tuple[float, float, float]):
        """메인(월드) 카메라 캘리브레이션 포인트 추가"""
        self.world_calibrator.add_point(robot_pos, world_cam_pos)

    def add_gripper_point(self, robot_pos: Tuple[float, float, float],
                          gripper_cam_pos: Tuple[float, float, float]):
        """그리퍼 카메라 캘리브레이션 포인트 추가"""
        self.gripper_calibrator.add_point(robot_pos, gripper_cam_pos)

    def remove_last_world_point(self):
        self.world_calibrator.remove_last_point()

    def remove_last_gripper_point(self):
        self.gripper_calibrator.remove_last_point()

    def clear_all(self):
        """모든 포인트 초기화"""
        self.world_calibrator.clear_points()
        self.gripper_calibrator.clear_points()

    # ─── 계산 및 저장 ───────────────────────────────────────────────────────
    def calculate_all(self) -> Dict[str, bool]:
        """
        두 카메라의 변환 행렬을 동시에 계산합니다.

        Returns:
            {"world": bool, "gripper": bool} - 각 캘리브레이션 성공 여부
        """
        world_ok   = self.world_calibrator.calculate_transform()
        gripper_ok = self.gripper_calibrator.calculate_transform()

        logging.info("=" * 50)
        logging.info("[MultiCalibrator] 캘리브레이션 결과 요약")
        logging.info(f"  메인(월드) 카메라: {'성공' if world_ok else '실패'}")
        if world_ok:
            err = self.world_calibrator.reprojection_error
            logging.info(f"    → 재투영 오차: {err:.2f} cm")
        logging.info(f"  그리퍼 카메라: {'성공' if gripper_ok else '실패'}")
        if gripper_ok:
            err = self.gripper_calibrator.reprojection_error
            logging.info(f"    → 재투영 오차: {err:.2f} cm")
        logging.info("=" * 50)

        return {"world": world_ok, "gripper": gripper_ok}

    def save_all(self):
        """두 카메라의 캘리브레이션 결과를 모두 저장합니다."""
        self.world_calibrator.save_calibration()
        self.gripper_calibrator.save_calibration()
        logging.info("[MultiCalibrator] 모든 캘리브레이션 파일 저장 완료")

    # ─── 좌표 변환 ──────────────────────────────────────────────────────────
    def world_to_robot(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """메인(월드) 카메라 좌표(cm) → 로봇 베이스 좌표(cm)"""
        return self.world_calibrator.camera_to_robot(x, y, z)

    def gripper_to_robot(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """그리퍼 카메라 좌표(cm) → 로봇 베이스 좌표(cm)"""
        return self.gripper_calibrator.camera_to_robot(x, y, z)

    # ─── 상태 조회 ──────────────────────────────────────────────────────────
    def get_status(self) -> Dict:
        """두 캘리브레이터의 현재 상태를 딕셔너리로 반환합니다."""
        return {
            "world": {
                "calibrated": self.world_calibrator.transform_matrix is not None,
                "valid":      self.world_calibrator.is_calibration_valid(),
                "num_points": len(self.world_calibrator.points),
                "error_cm":   self.world_calibrator.reprojection_error
            },
            "gripper": {
                "calibrated": self.gripper_calibrator.transform_matrix is not None,
                "valid":      self.gripper_calibrator.is_calibration_valid(),
                "num_points": len(self.gripper_calibrator.points),
                "error_cm":   self.gripper_calibrator.reprojection_error
            }
        }
