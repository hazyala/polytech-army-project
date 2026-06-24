# flask_server.py
from flask import Flask, Response, request, jsonify
from flask_socketio import SocketIO, emit
import cv2
import json
import time
import threading 
import shared_data as shared
import numpy as np


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# async_mode='threading'을 명시하여 표준 스레드 사용
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ====================================
# [HTTP] Video Stream
# ====================================
def gen():
    while True:
        with shared.frame_lock:
            if shared.latest_frame is None:
                time.sleep(0.01)
                continue
            frame_to_send = shared.latest_frame.copy()
        
        _, jpeg = cv2.imencode('.jpg', frame_to_send, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.05)


def gen_ee():
    while True:
        with shared.frame_lock:
            if shared.latest_ee_frame is None:
                time.sleep(0.01)
                continue
            frame_to_send = shared.latest_ee_frame.copy()
        
        _, jpeg = cv2.imencode('.jpg', frame_to_send, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.05)

# ============ GET Video ============
@app.route("/")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ============ GET Image ============
@app.route("/image")
def snapshot():
    with shared.frame_lock:
        if shared.latest_frame is None:
            return "No frame yet", 503
        frame = shared.latest_frame.copy()
        
    _, jpeg = cv2.imencode(".jpg", frame)
    return Response(jpeg.tobytes(), mimetype="image/jpeg")


# ============ GET Depth ============
@app.route("/depth")
def get_depth():
    with shared.frame_lock:
        depth = shared.latest_frame_depth

    return jsonify(depth.tolist())



# ============ GET EE-Video ============
@app.route("/ee-video")
def ee_video_feed():
    return Response(gen_ee(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ============ GET EE-Image ============
@app.route("/ee-image")
def ee_snapshot():
    with shared.frame_lock:
        if shared.latest_ee_frame is None:
            return "No frame yet", 503
        frame = shared.latest_ee_frame.copy()
        
    _, jpeg = cv2.imencode(".jpg", frame)
    return Response(jpeg.tobytes(), mimetype="image/jpeg")


# ============ GET EE-Depth ============
@app.route("/ee-depth")
def get_ee_depth():
    with shared.frame_lock:
        depth = shared.latest_ee_frame_depth

    return jsonify(depth.tolist())



# ====================================
# [WebSocket] 데이터 송출 (Server -> Client)
# ====================================
def broadcast_data():
    while True:
        robot_packet = {}
        object_packet = {}

        # ============ 로봇 상태 (ee, joints) ============
        with shared.state_lock:
            robot_packet['ee'] = shared.robot_state.copy()
            robot_packet['joints'] = shared.joints_degrees[:]
            robot_packet['gripper'] = shared.gripper_state
            
            # 오브젝트 상태 (좌표, 직선거리)
            object_packet['object'] = shared.object_info.copy()

        # ============ 데이터 전송 ============
        try:
            socketio.emit('robot_state', robot_packet)
            socketio.emit('object_state', object_packet)
        except Exception:
            pass 
        
        time.sleep(0.05) 



# ====================================
# [WebSocket] 제어 명령 수신
# ====================================
@socketio.on('connect')
def handle_connect():
    print(">>> Client Connected")


# ============ Joint ============
@socketio.on('set_joints')
def handle_set_joints(data):
    if 'joints' in data:
        with shared.cmd_lock:
            shared.command["joint_cmd"] = data['joints']

# ============ Gripper ============
@socketio.on('set_gripper')
def handle_set_gripper(data):
    if 'gripper' in data:
        with shared.cmd_lock:
            shared.command["gripper_cmd"] = data['gripper']


# ============ 목표 좌표 ============
@socketio.on('set_pos')
def handle_set_pos(data):
    if 'pos' in data:
        with shared.cmd_lock:
            shared.command["target_pos"] = data['pos']


# ============ POST 로봇 힘 ============
@socketio.on('set_force')
def handle_set_force(data):
    if "force" in data:
        with shared.cmd_lock:
            shared.command["force"] = data["force"]


# ============ 최대 속도 ============
@socketio.on('set_max_velocity')
def handle_set_max_velocity(data):
    if 'max_velocity' in data:
        with shared.cmd_lock:
            shared.command["max_velocity"] = data['max_velocity']


# ============ 오브젝트 생성/제거  ============
@socketio.on('set_object')
def handle_set_object(data):
    with shared.cmd_lock:
        shared.command["object_cmd"] = data


# ============ 오브젝트 위치 제어 ============
@socketio.on('set_object_pos')
def handle_set_object_pos(data):
    if 'pos' in data:
        with shared.cmd_lock:
            shared.command["object_pos_cmd"] = data['pos']



# ====================================
# 서버 실행 함수
# ====================================
def run_flask():
    print(">>> Flask SocketIO Server Started on port 5000 (Threading Mode)")
    
    # 데이터 전송 백그라운드 스레드 시작
    t = threading.Thread(target=broadcast_data, daemon=True)
    t.start()
    
    # allow_unsafe_werkzeug=True 옵션 추가
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)