import logging
import numpy as np
import math

# PyBullet 라이브러리 가용성 체크
PYBULLET_AVAILABLE = False
try:
    import pybullet as p
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False
    logging.warning("[PyBulletProjection] pybullet 모듈을 찾을 수 없습니다. 시뮬레이션 투영 기능을 사용할 수 없습니다.")

# PyBullet 카메라 설정 (pybullet_sim.py와 일치해야 함)
CAMERA_CONFIG = {
    "width": 600,
    "height": 480,
    "fov": 60,  # degrees (수직 FOV)
    "near": 0.01,
    "far": 10.0,
    "camera_eye": [0.5, 0.0, 0.5],     # 카메라 위치 (m)
    "camera_target": [0.0, 0.0, 0.0],  # 카메라 타겟 (m)
    "camera_up": [0.0, 0.0, 1.0]       # 상단 벡터
}

def _get_camera_parameters():
    """
    PyBullet API를 통해 View/Projection Matrix(뷰/프로젝션 행렬: 3D 공간을 2D 화면으로 투영하기 위한 수학적 변환표)를 계산하고
    Intrinsic(내인자: 렌즈 속성) 및 Extrinsic(외인자: 카메라 위치/각도) 행렬을 추출합니다.
    """
    # PyBullet이 없는 경우 더미 데이터 반환 (테스트 및 비-시뮬레이션 환경 지원)
    if not PYBULLET_AVAILABLE:
        logging.warning("[PyBulletProjection] PyBullet 미설치로 인해 더미 카메라 파라미터를 사용합니다.")
        return 600.0, 600.0, 300.0, 240.0, np.eye(4)

    width = CAMERA_CONFIG["width"]
    height = CAMERA_CONFIG["height"]
    
    # 1. View Matrix(뷰 행렬: 월드 좌표를 카메라 중심 좌표로 변환) 계산 
    # (OpenGL 포맷: 4x4 리스트, Column-major: 열 우선 정렬 방식)
    view_matrix_list = p.computeViewMatrix(
        cameraEyePosition=CAMERA_CONFIG["camera_eye"],
        cameraTargetPosition=CAMERA_CONFIG["camera_target"],
        cameraUpVector=CAMERA_CONFIG["camera_up"]
    )
    # Row-major(행 우선 정렬 방식) numpy 배열로 변환
    view_matrix = np.array(view_matrix_list).reshape(4, 4, order='F')
    
    # Camera -> World (Inverse View Matrix: 카메라 좌표를 다시 월드 좌표로 되돌리는 역행렬)
    # CamToWorld = [Right  Up  -Forward  Eye]
    #              [  0    0       0      1 ]
    cam_to_world = np.linalg.inv(view_matrix)
    
    # 2. Projection Matrix(투영 행렬: 카메라 좌표를 화면의 2D 좌표로 변환) 계산
    # Camera -> NDC(기기 독립적인 표준 좌표계) 변환 행렬
    aspect = width / height
    proj_matrix_list = p.computeProjectionMatrixFOV(
        fov=CAMERA_CONFIG["fov"],
        aspect=aspect,
        nearVal=CAMERA_CONFIG["near"],
        farVal=CAMERA_CONFIG["far"]
    )
    proj_matrix = np.array(proj_matrix_list).reshape(4, 4, order='F')
    
    # 3. Intrinsic(내인자: 렌즈 고유 파라미터) 추출
    # P[0,0] = 2*fx/W  => fx = P[0,0] * W / 2
    # P[1,1] = 2*fy/H  => fy = P[1,1] * H / 2
    
    # 주의: PyBullet(OpenGL) Projection Matrix는 Screen Space가 아닌 NDC(-1~1)로 보냅니다.
    # fx, fy는 NDC 기준 스케일입니다. 픽셀 단위 fx, fy로 변환합니다.
    
    # P[0,0] = 1 / (aspect * tan(fov/2))
    # Pixel FX = W / (2 * tan(fov/2 * aspect?? No)) = W/2 * P[0,0]
    fx = proj_matrix[0, 0] * width / 2.0
    fy = proj_matrix[1, 1] * height / 2.0
    
    cx = width / 2.0
    cy = height / 2.0
    
    return fx, fy, cx, cy, cam_to_world

# 파라미터 초기화
FX, FY, CX, CY, CAM_TO_WORLD_MAT = _get_camera_parameters()

logging.info(f"[PyBulletProjection] 재계산된 파라미터: fx={FX:.2f}, fy={FY:.2f}, cx={CX:.2f}, cy={CY:.2f}")
logging.info(f"[PyBulletProjection] Cam->World:\n{CAM_TO_WORLD_MAT}")


def pixel_to_3d(pixel_x: int, pixel_y: int, depth_m: float) -> tuple:
    """
    PyBullet 픽셀 좌표를 월드 3D 좌표(cm)로 변환합니다.
    API와 동일한 매트릭스를 사용하여 오차를 제거했습니다.
    """
    if not PYBULLET_AVAILABLE:
        logging.error("[PyBulletProjection] pybullet 모듈이 없어 좌표 변환을 수행할 수 없습니다.")
        return 0.0, 0.0, 0.0
    
    # 1. 픽셀 → 카메라 좌표계 (View Space)
    # OpenGL 카메라 좌표계: X(Right), Y(Up), Z(Backward, 즉 -Forward)
    # 하지만 PyBullet의 View Matrix는 LookAt 방식이므로
    # View Space에서 물체는 -Z 방향에 있습니다. (Camera looks down -Z)
    
    # Pinhole Back-projection
    # x_cam = (u - cx) * depth / fx
    # y_cam = -(v - cy) * depth / fy  (이미지 Y는 아래로 증가, GL Y는 위로 증가 -> 반전)
    # z_cam = -depth (카메라가 보는 방향이 -Z)
    
    x_view = (pixel_x - CX) * depth_m / FX
    y_view = -(pixel_y - CY) * depth_m / FY
    z_view = -depth_m
    
    # 동차 좌표 (Homogeneous coordinates)
    view_pos = np.array([x_view, y_view, z_view, 1.0])
    
    # 2. 카메라 좌표계 → 월드 좌표계
    world_pos = CAM_TO_WORLD_MAT @ view_pos
    
    # 3. m → cm 변환
    x_cm = world_pos[0] * 100.0
    y_cm = world_pos[1] * 100.0
    z_cm = world_pos[2] * 100.0
    
    logging.info(
        f"[PyBulletProjection] "
        f"픽셀=({pixel_x}, {pixel_y}), depth={depth_m:.4f}m → "
        f"View=({x_view:.3f}, {y_view:.3f}, {z_view:.3f}) → "
        f"월드=({x_cm:.2f}, {y_cm:.2f}, {z_cm:.2f})cm"
    )
    
    return x_cm, y_cm, z_cm

def pixel_to_view_space(pixel_x: int, pixel_y: int, depth_m: float) -> tuple:
    """
    [Helper] 픽셀 좌표를 카메라 기준 3D 좌표(View Space, cm 단위)로 변환합니다.
    월드 변환 전 단계의 순수 로컬 좌표가 필요할 때 사용합니다 (예: 그리퍼 카메라).
    """
    if not PYBULLET_AVAILABLE: return 0.0, 0.0, 0.0

    # Pinhole Back-projection
    x_view = (pixel_x - CX) * depth_m / FX
    y_view = -(pixel_y - CY) * depth_m / FY
    z_view = -depth_m # PyBullet View Space는 -Z 방향
    
    # m -> cm
    return x_view * 100.0, y_view * 100.0, z_view * 100.0


def calculate_planar_depth(world_x_cm, world_y_cm, world_z_cm):
    """
    월드 좌표(cm)에 해당하는 점의 카메라 기준 Planar Depth(평면 깊이: 카메라 정면에서 수직으로 잰 거리)를 계산합니다.
    (Oracle Depth: 물리 엔진이 알려주는 오차 없는 완벽한 정답 거리를 가정할 때 사용)
    """
    # 1. cm -> m 변환
    world_pos_m = np.array([world_x_cm/100.0, world_y_cm/100.0, world_z_cm/100.0, 1.0])
    
    # 2. World -> Camera (View Matrix: 뷰 행렬) 변환
    # CAM_TO_WORLD_MAT의 역행렬이 View Matrix입니다.
    view_matrix = np.linalg.inv(CAM_TO_WORLD_MAT)
    
    view_pos = view_matrix @ world_pos_m
    
    # 3. View Space에서 카메라는 -Z 방향을 바라봅니다.
    # 따라서 Planar Depth는 -z_view 입니다.
    return -view_pos[2]

    
    return -view_pos[2]

# [Shared Memory Access]
# User Request: "Can't we just get it from memory?" -> YES.
# We connect to the existing PyBullet Physics Server via Shared Memory to read the True Orientation.
_SHARED_CLIENT_ID = None

def _get_real_ee_state_via_shared_memory(robot_id=0, ee_index=None):
    """
    [Direct Memory Access]
    실행 중인 PyBullet 시뮬레이터의 메모리에 직접 접근하여
    서버가 보내주지 않는 '회전값(Orientation)'을 조회합니다.
    """
    global _SHARED_CLIENT_ID
    
    if not PYBULLET_AVAILABLE: return None, None
    
    try:
        # 1. Connection (Lazy Init)
        if _SHARED_CLIENT_ID is None:
            # GUI 서버(id=0)가 이미 있을 수 있음
            if p.isConnected():
                _SHARED_CLIENT_ID = 0
            else:
                # 없으면 SHARED_MEMORY로 접속 시도
                try:
                    _SHARED_CLIENT_ID = p.connect(p.SHARED_MEMORY)
                except:
                    return None, None
                    
        if _SHARED_CLIENT_ID is None or _SHARED_CLIENT_ID < 0:
            return None, None, None
            
        # 2. Robot ID Finding (Cache needed)
        target_robot = robot_id # Default 0
        
        # Auto-detect robot (Body with joints)
        # 이미 찾았으면 패스, 아니면 검색
        if target_robot == 0:
            num_bodies = p.getNumBodies(physicsClientId=_SHARED_CLIENT_ID)
            for i in range(num_bodies):
                if p.getNumJoints(i, physicsClientId=_SHARED_CLIENT_ID) > 0:
                    target_robot = i
                    break
        
        target_ee = ee_index
        
        if target_ee is None:
             # 검색: 'end_effector' or 'ee' or 'tip'
             num_joints = p.getNumJoints(target_robot, physicsClientId=_SHARED_CLIENT_ID)
             for i in range(num_joints):
                 info = p.getJointInfo(target_robot, i, physicsClientId=_SHARED_CLIENT_ID)
                 # info[1]: jointName, info[12]: linkName
                 # [Fix] 하이픈/언더바 모두 허용 및 'link5' (DofBot 일반적 말단) 추가
                 link_name = info[12]
                 joint_name = info[1]
                 if b'ee' in joint_name or b'tip' in joint_name or b'end_effector' in link_name or b'end-effector' in link_name:
                     target_ee = i
                     break
             
             if target_ee is None: 
                 # 만약 못 찾으면 link5 시도 (DofBot)
                 for i in range(num_joints):
                     info = p.getJointInfo(target_robot, i, physicsClientId=_SHARED_CLIENT_ID)
                     if b'link5' in info[12]:
                         target_ee = i
                         break
                         
             if target_ee is None: target_ee = num_joints - 1
             
             # 검증 로깅
             debug_info = p.getJointInfo(target_robot, target_ee, physicsClientId=_SHARED_CLIENT_ID)
             logging.info(f"[PyBulletProjection] Shared Memory EE Link Selected: ID={target_ee}, Name={debug_info[12].decode()}, Joint={debug_info[1].decode()}")

        # 3. Get State
        state = p.getLinkState(target_robot, target_ee, computeForwardKinematics=True, physicsClientId=_SHARED_CLIENT_ID)
        # state[4]=Pos, state[5]=Orn
        return state[4], state[5], target_ee
        
    except Exception as e:
        logging.error(f"[PyBulletProjection] Shared Memory Access Fail: {e}")
        return None, None, None

def project_gripper_camera_to_world(point_view: list, ee_pos: list, ee_orn: list) -> list:
    """
    [Dynamic Kinematics] 
    그리퍼 카메라에 찍힌 좌표(View Space)를 로봇 월드 좌표(World Space)로 변환합니다.
    
    서버가 회전값(Orientation)을 안 보내주는 경우([0,0,0,1]),
    공유 메모리에서 진짜 회전값을 찾아와서 교체해 줍니다.
    """
    if not PYBULLET_AVAILABLE: return point_view
    
    # 1. 회전값 누락 확인
    # 서버가 보내준 ee_orn이 Identity([0,0,0,1] = 회전 없음)라면, 
    # 실제로는 회전값이 누락된 것이므로 복구가 필요합니다.
    need_fix = False
    
    if ee_orn == [0,0,0,0]: # 비정상
        need_fix = True
    elif abs(ee_orn[0]) < 1e-4 and abs(ee_orn[1]) < 1e-4 and abs(ee_orn[2]) < 1e-4 and abs(ee_orn[3]-1) < 1e-4:
        need_fix = True
        
    if need_fix:
        logging.warning("[PyBulletProjection] EE 회전값 누락(Identity) 감지! 공유 메모리에서 복구를 시도합니다.")
        # [Improvement] 공유 메모리 조회
        # 로봇이 실제로 어떻게 꺾여 있는지 메모리에서 직접 가져옵니다.
        mem_pos, mem_orn, _ = _get_real_ee_state_via_shared_memory()
        
        if mem_pos and mem_orn:
            # [Validation] 데이터 신뢰성 검증
            # 서버가 보낸 위치(ee_pos)와 메모리 상의 위치(mem_pos)는 거의 같아야 합니다.
            diff = math.sqrt((ee_pos[0]-mem_pos[0])**2 + (ee_pos[1]-mem_pos[1])**2 + (ee_pos[2]-mem_pos[2])**2)
            
            if diff > 0.05: # 5cm 이상 차이나면 뭔가 이상한 것 (동기화 지연 등)
                logging.warning(f"[PyBulletProjection] 위치 불일치 경고: {diff*100:.1f}cm 차이남. (데이터 갱신 지연 가능성)")
            else:
                # 위치가 맞으면 회전값도 믿고 씁니다.
                ee_orn = mem_orn

    # 2. 좌표 변환: 카메라(View) -> 손끝(EE) 로컬 좌표
    # [설명] PyBullet 카메라 좌표계와 로봇 링크 좌표계의 축 방향을 맞춥니다.
    # View Forward(-Z)  -> Link Z (앞)
    # View Up(Y)        -> Link -X (아래)
    # View Right(X)     -> Link -Y (왼쪽)
    # 결과: [-Y_view, -X_view, -Z_view]
    p_local = np.array([-point_view[1], -point_view[0], -point_view[2]]) # cm 단위
    
    # 3. 좌표 변환: 손끝(EE) -> 로봇 베이스(World)
    # 회전 행렬(Rotation Matrix) 적용
    rot_matrix = np.array(p.getMatrixFromQuaternion(ee_orn)).reshape(3, 3)
    
    # 평행이동(Translation) 적용 (m -> cm 변환)
    t_world = np.array(ee_pos) * 100.0
    
    p_world = rot_matrix @ p_local + t_world
    
    return p_world.tolist()
