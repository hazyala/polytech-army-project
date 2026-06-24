# app.py
import streamlit as st
import socketio
import time
import queue


API_URL = "http://localhost:5000"

# ====================================
# 페이지 설정
# ====================================
st.set_page_config(
    page_title="PyBullet Robot UI", 
    layout="wide",
    initial_sidebar_state="collapsed"
)



# ====================================
# 소켓 관리자 (캐싱하여 재실행 방지)
# ====================================
@st.cache_resource
def get_socket_manager():
    sio = socketio.Client(reconnection=True)

    robot_q  = queue.Queue()
    object_q = queue.Queue()

    @sio.on('robot_state')
    def on_robot(data):
        if robot_q.qsize() > 2:
            robot_q.get_nowait()
        robot_q.put(data)

    @sio.on('object_state')
    def on_object(data):
        if object_q.qsize() > 2:
            object_q.get_nowait()
        object_q.put(data)

    return sio, robot_q, object_q

sio, robot_q, object_q = get_socket_manager()



# ====================================
# 세션 상태 초기화 (새로고침 시 실행)
# ====================================
# 서버 데이터 기본값
if 'server_data' not in st.session_state:
    st.session_state.server_data = {
        "ee": {"x": 0.0, "y": 0.0, "z": 0.0},
        "joints": [0.0, 0.0, 0.0, 0.0, 0.0],
        "gripper": 0.0,
        "object": {"exists": False, "x": 0.0, "y": 0.0, "z": 0.0, "distance": 0.0}
    }

# UI 입력 상태 변수들
if "joints" not in st.session_state: st.session_state.joints = [0.0] * 5
if "gripper" not in st.session_state: st.session_state.gripper = 0.0
if "max_velocity" not in st.session_state: st.session_state.max_velocity = 20.0
if "object_type" not in st.session_state: st.session_state.object_type = "teddy"
if "object_fix" not in st.session_state: st.session_state.object_fix = False



# ====================================
# 연결 관리 및 데이터 동기화
# ====================================
# 소켓이 끊겨있으면 연결 시도
if not sio.connected:
    try:
        sio.connect(API_URL, transports=['websocket', 'polling'], wait_timeout=3)
        print(">>> Socket Connected")
    except Exception as e:
        pass


# 큐에 쌓인 최신 데이터 하나만 가져와서 세션에 반영
# Robot
if not robot_q.empty():
    while not robot_q.empty():
        latest = robot_q.get_nowait()
    st.session_state.server_data['ee'] = latest['ee']
    st.session_state.server_data['joints'] = latest['joints']
    st.session_state.server_data['gripper'] = latest['gripper']

# Object
if not object_q.empty():
    while not object_q.empty():
        latest = object_q.get_nowait()
    st.session_state.server_data['object'] = latest['object']



# ====================================
# 명령 전송 함수
# ====================================
# ============ Joints ============
def send_joint_command():
    joints = [st.session_state[f"joint_{i}"] for i in range(5)]
    if sio.connected:
        sio.emit('set_joints', {'joints': joints})

# ============ Gripper ============
def send_gripper_command():
    val = st.session_state["gripper"]
    if sio.connected:
        sio.emit('set_gripper', {'gripper': val})

# ============ 목표 좌표 ============
def send_pos_command():
    pos = [st.session_state.input_arm_x, st.session_state.input_arm_y, st.session_state.input_arm_z]
    if sio.connected:
        sio.emit('set_pos', {'pos': pos})
        
# ============ 최대 속도 ============
def send_velocity_cmd():
    val = st.session_state["max_velocity"]
    if sio.connected:
        sio.emit('set_max_velocity', {'max_velocity': val})

# ============ 오브젝트 생성/제거 ============
def send_object_cmd():
    is_created = st.session_state.get(f"{st.session_state.object_type}_created", False)
    op = "delete" if is_created else "create"
    body = {"object": st.session_state.object_type, "op": op, "fix": st.session_state.object_fix}
    
    if sio.connected:
        sio.emit('set_object', body)
        # 버튼 상태 즉시 반영
        target = f"{st.session_state.object_type}_created"
        st.session_state[target] = not st.session_state.get(target, False)

# ============ 오브젝트 좌표 제어 ============
def send_object_pos_command():
    pos = [st.session_state.input_obj_x, st.session_state.input_obj_y, st.session_state.input_obj_z]
    if sio.connected:
        sio.emit('set_object_pos', {'pos': pos})



# ====================================
# UI 레이아웃 구성
# ====================================
# 데이터 단축 참조
srv = st.session_state.server_data
ee = srv['ee']
joints_fb = srv['joints']
gripper_state = srv["gripper"]
obj = srv['object']


# 사이드바에 연결 상태 표시
with st.sidebar:
    st.header("System Status")
    status_color = "green" if sio.connected else "red"
    status_text = "Connected" if sio.connected else "Disconnected"
    st.markdown(f"Server: :{status_color}[{status_text}]")
    if st.button("Reconnect Force"):
        sio.disconnect()
        st.rerun()

col_1, col_2, col_3 = st.columns([2, 1, 1])


# ============ Column 1: Camera & Robot Joints ============
with col_1:
    # Camera
    st.subheader("Live Feed")
    st.markdown(f'<img src="{API_URL}/" width="100%" style="border-radius: 10px;">', unsafe_allow_html=True)
    
    # Joint Control
    st.divider()
    st.subheader("Joint Control")
    joint_limits = [[-90.0,90.0], [-55.0,55.0], [-65.0,65.0], [-90.0,90.0], [-90.0,90.0]]
    # Joint Slider
    for i in range(5):
        st.slider(
            f"Joint {i+1}", 
            joint_limits[i][0], joint_limits[i][1], 
            joints_fb[i],
            step=0.1,
            key=f"joint_{i}", 
            on_change=send_joint_command
        )

    # Gripper & Velocity
    col_g, col_v = st.columns(2)
    with col_g:
        st.slider("Gripper", 0.0, 0.06, step=0.001, key="gripper", on_change=send_gripper_command)
    with col_v:
        st.slider("Velocity", 0.0, 20.0, step=0.1, key="max_velocity", on_change=send_velocity_cmd)


# ============ Column 2: IK Control & State ============
with col_2:
    # IK Control
    st.subheader("IK Control")
    st.number_input("Target X", value=0.0, step=0.01, key="input_arm_x")
    st.number_input("Target Y", value=0.0, step=0.01, key="input_arm_y")
    st.number_input("Target Z", value=0.0, step=0.01, key="input_arm_z")
    st.button("목표 좌표 전송", on_click=send_pos_command, use_container_width=True)

    # End-Effector
    st.divider()
    st.subheader("Robot State")
    st.info(f"End-Effector: ({ee['x']}, {ee['y']}, {ee['z']})")
    
    # Joints
    with st.expander("Joint Angles"):
        st.write(f"Angles: {joints_fb}")

    st.info(f"gripper: {gripper_state}")


# ============ Column 3: Object Control ============
with col_3:
    st.subheader("Object Manager")
    
    # 라벨 설정
    is_created = st.session_state.get(f"{st.session_state.object_type}_created", False)
    btn_label = "오브젝트 제거" if is_created else "오브젝트 생성"
    btn_type = "primary" if not is_created else "secondary"

    # 오브젝트 종류/고정 여부 선택
    st.radio("Object Type", ("teddy", "duck", "soccerball", "mug"), key="object_type", horizontal=True)
    st.checkbox("오브젝트 고정", key="object_fix")
    
    # 오브젝트 생성/제거
    st.button(btn_label, type=btn_type, on_click=send_object_cmd, use_container_width=True)

    # 오브젝트 위치 제어
    st.divider()
    st.subheader("Object Position")
    st.number_input("Obj X", value=0.1, step=0.01, key="input_obj_x")
    st.number_input("Obj Y", value=0.0, step=0.01, key="input_obj_y")
    st.number_input("Obj Z", value=0.0, step=0.01, key="input_obj_z")
    st.button("오브젝트 이동", on_click=send_object_pos_command, use_container_width=True)

    if obj['exists']:
        st.success("Object Detected")
        st.write(f"Pos: ({obj['x']}, {obj['y']}, {obj['z']})")
        st.write(f"Dist: {obj['distance']}")
    else:
        st.warning("No Object")



# ====================================
# 자동 갱신 루프
# ====================================
time.sleep(0.05)
st.rerun()