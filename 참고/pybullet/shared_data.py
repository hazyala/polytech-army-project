import threading

# ====================================
# 동기화 Locks
# ====================================
frame_lock = threading.Lock()
state_lock = threading.Lock()
cmd_lock = threading.Lock() # 명령 전달용 락



# ====================================
# 공유 데이터
# ====================================
latest_frame = None
latest_frame_depth = None
latest_ee_frame = None
latest_ee_frame_depth = None


# ============ 로봇 정보 (Sim -> Flask) ============
robot_state = {"x": 0.0, "y": 0.0, "z": 0.0}
joints_degrees = [0, 0, 0, 0, 0]
gripper_state = None


# ============ 오브젝트 정보 (Sim -> Flask) ============
object_info = {
    "exists": False,
    "x": 0.0, "y": 0.0, "z": 0.0,
    "distance": 0.0 # 원점으로부터 직선거리
}


# ============ 제어 명령 (Flask -> Sim) ============
command = {
    "target_pos": None,     # IK 목표 좌표 {"pos": [x, y, z]}
    "joint_cmd": None,      # Joint 각도 {"joints": [deg1, deg2, deg3, deg4, deg5]}
    "gripper_cmd": None,    # Gripper 제어 {"gripper": 0.0 ~ 0.06}
    "force": 100,           # 로봇 힘 {"force": int}
    "max_velocity": 100,    # 로봇 최대 속도 {"max_velocity": int}
    "object_cmd": None,     # 오브젝트 생성/삭제 {"op": "create", "object": "teddy", "fix": False}
    "object_pos_cmd": None # 오브젝트 이동 {"pos": [x, y, z]}
}