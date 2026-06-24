import os
from pathlib import Path
from dotenv import load_dotenv # 환경 변수 로드용

class PathConfig:
    """pathlib을 사용한 경로 관리 클래스입니다."""
    # pathlib 사용 이유는, 전역 관리가 쉽기 때문 (하드코딩 방지)
    # BASE_DIR : 프로젝트의 최상위 디렉토리
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # 7 Layer Pipeline 및 주요 디렉토리
    SENSOR_DIR = BASE_DIR / "sensor"
    STATE_DIR = BASE_DIR / "state"
    BRAIN_DIR = BASE_DIR / "brain"
    STRATEGY_DIR = BASE_DIR / "strategy"
    EXPRESSION_DIR = BASE_DIR / "expression"
    EMBODIMENT_DIR = BASE_DIR / "embodiment"
    MEMORY_DIR = BASE_DIR / "memory"
    
    # 공유 및 인터페이스
    SHARED_DIR = BASE_DIR / "shared"
    INTERFACE_DIR = BASE_DIR / "interface"
    
    # 데이터 및 문서
    DATA_DIR = BASE_DIR / "data"
    MODEL_DIR = DATA_DIR / "models"
    LOG_DIR = DATA_DIR / "logs"
    DOCS_DIR = BASE_DIR / "docs"

    # 캘리브레이션 데이터 저장 디렉토리
    CALIBRATION_DIR = DATA_DIR / "calibration"

    @staticmethod
    def ensure_dirs():
        """필요한 데이터 디렉토리가 없으면 생성합니다."""
        for path in [PathConfig.DATA_DIR, PathConfig.MODEL_DIR, PathConfig.LOG_DIR, PathConfig.CALIBRATION_DIR]:
            path.mkdir(parents=True, exist_ok=True)

class GlobalConfig:
    """시스템 전역 설정 클래스입니다."""
    SIM_MODE = False # 현재 시스템이 시뮬레이션(PyBullet) 모드인지, 실제 로봇 모드인지 결정하는 스위치
    
    # 브레인(Brain) 설정
    VLM_ENDPOINT = "http://ollama.aikopo.net/api/generate" # 엔드포인트를 통해 호출할 모델 주소
    VLM_MODEL = "gemma3:27b" # 엔드포인트를 통해 호출할 모델 이름
    
    # PyBullet 서버 설정
    PYBULLET_HOST = "localhost"
    PYBULLET_PORT = 5000 #서버 중복 연결 오류 나면 5001로 변경
    SIM_SERVER_URL = f"http://{PYBULLET_HOST}:{PYBULLET_PORT}"
    
    # DOFBOT 서버 설정 (클라이언트로 연결)
    # DOFBOT_ROBOT_ARM-main/main.py 서버와 통신합니다
    DOFBOT_SERVER_HOST = "192.168.25.100"  
    DOFBOT_SERVER_PORT = 5000
    DOFBOT_SERVER_URL = f"http://{DOFBOT_SERVER_HOST}:{DOFBOT_SERVER_PORT}"
    
    # API 서버 포트
    API_PORT = 8000
    
    # 감정(Emotion) 설정
    EMOTION_UPDATE_INTERVAL = 0.5  # 초 단위 (저수준 LLM 업데이트 주기)
    EMOTION_RENDER_FPS = 60        # 초당 프레임 수 (고수준 보간 루프로 60fps)
    
    # RealSense 카메라 설정
    REALSENSE_ENABLE_GRIPPER_CAM = True  # 그리퍼 카메라 활성화 여부
    REALSENSE_ENABLE_IMU = True  # IMU(가속도/자이로) 데이터 활성화 여부
    CAMERA_FPS = 15 # 카메라 FPS (대역폭 최적화)
    REALSENSE_FRAME_TIMEOUT_MS = 3000  # 프레임 대기 타임아웃 (ms) - 5초에서 3초로 감소
    REALSENSE_MAX_TIMEOUT_RETRIES = 5  # 연속 타임아웃 최대 허용 횟수
    
    # RealSense 시리얼 번호 설정
    REALSENSE_WORLD_SERIAL = "234222302678"
    REALSENSE_GRIPPER_SERIAL = "234322306432"

    # 캘리브레이션 데이터 파일 경로 (카메라→로봇 변환 행렬)
    CALIBRATION_FILE_WORLD   = PathConfig.DATA_DIR / "calibration" / "world_camera_calibration.json"
    CALIBRATION_FILE_GRIPPER = PathConfig.DATA_DIR / "calibration" / "gripper_camera_calibration.json"
    # 카메라 간 상호 변환 행렬 (그리퍼→메인 카메라 Extrinsics)
    CALIBRATION_FILE_EXTRINSICS = PathConfig.DATA_DIR / "calibration" / "camera_extrinsics.json"

    # 레거시 호환성 (기존 코드와의 호환을 위해 유지)
    ROBOT_IP = DOFBOT_SERVER_URL  # 기존 ROBOT_IP를 DOFBOT_SERVER_URL로 매핑 

class CameraConfig:
    """카메라 설치 위치 및 오프셋 설정 클래스입니다."""
    # 시뮬레이션 환경 (PyBullet) 오프셋
    # PyBullet 카메라 위치: cameraEyePosition=[0.5, 0, 0.5] (m 단위)
    # → cm 단위로 변환: X=50cm, Y=0cm, Z=50cm
    SIM_OFFSET = {"x": 50.0, "y": 0.0, "z": 50.0}  # cm 단위
    
    # 실물 환경 (Intel RealSense) 레거시 오프셋 (수동 측정 추정치)
    # [주의] 아직 공식 캘리브레이션 미완료. CalibrationConfig.RED_TAPE_ROBOT_POS 기반
    #        CameraCalibrator 정식 캘리브레이션 완료 후 이 값은 더 이상 사용하지 않습니다.
    REAL_OFFSET = {"x": 63.0, "y": 0.0, "z": 54.0}  # cm 단위 (임시 추정치)


class CalibrationConfig:
    """
    캘리브레이션 마커(빨간 테이프) 기준 좌표 설정 클래스입니다.

    [마커 설명]
    - 소재: 빨간 테이프 (Red Tape)
    - 검출 방식: HSV 색상 필터링 (calibration_system.py RedTapeDetector)
    - 좌표계: 로봇 베이스 좌표계 (단위: cm)

    [수집 방식]
    - test_calibration_wizard.py를 통해 로봇을 마커 위에 직접 이동시키고
      end-effector 좌표를 자동으로 읽어 포인트를 수집합니다.
    - RED_TAPE_ROBOT_POS는 검증용 참고 좌표로만 사용됩니다.
    """
    # 빨간 테이프 마커의 로봇 베이스 기준 참고 좌표 (cm, 검증용)
    RED_TAPE_ROBOT_POS = {"x": 0.0, "y": 7.0, "z": 1.0}

    # 캘리브레이션 최소 요구 포인트 수 (정확한 Affine 행렬을 위해 6개 이상 권장)
    MIN_CALIBRATION_POINTS = 6

    # 재투영 오차 합격 기준 (cm) - 이 값 이하면 캘리브레이션 성공으로 판단
    MAX_REPROJECTION_ERROR_CM = 5.0

    # 빨간 마커 HSV 검출 파라미터 (조명 환경에 따라 조정)
    RED_HSV_LOWER1 = [0,   120,  70]   # 빨간 범위 1 (hue 0~10)
    RED_HSV_UPPER1 = [10,  255, 255]
    RED_HSV_LOWER2 = [170, 120,  70]   # 빨간 범위 2 (hue 170~180)
    RED_HSV_UPPER2 = [180, 255, 255]
    RED_MIN_AREA   = 200               # 최소 검출 면적 (픽셀²), 작으면 잡음 무시


# 환경 변수 로드 
# .env 파일에서 환경 변수를 로드할 수도 있으니까 미리 만들어둠. (.env.example로 만들어둠 내용은 없음)
load_dotenv(PathConfig.BASE_DIR / ".env")
PathConfig.ensure_dirs()