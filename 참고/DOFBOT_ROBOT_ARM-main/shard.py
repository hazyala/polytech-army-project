import threading

command = {
    "target_pos": None,
    "gripper_cmd": None,
    "torque_cmd": None
}

robot_state = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0
}

joints_degrees = [0,0,0,0,0]

cmd_lock = threading.Lock()
state_lock = threading.Lock()
