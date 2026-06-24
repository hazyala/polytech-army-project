import time
import math
import shared
from dofbot_simple import DofbotSimple


def run_robot_loop():

    bot = None

    try:

        bot = DofbotSimple("dofbot.urdf")

        while True:

            target_pos = None
            gripper_cmd = None
            torque_cmd = None
            
            with shared.cmd_lock:
                if shared.command["torque_cmd"] is not None:
                    torque_cmd = shared.command["torque_cmd"]
                    shared.command["torque_cmd"] = None
                if shared.command["target_pos"] is not None:
                    target_pos = shared.command["target_pos"]
                    shared.command["target_pos"] = None

                if shared.command["gripper_cmd"] is not None:
                    gripper_cmd = shared.command["gripper_cmd"]
                    shared.command["gripper_cmd"] = None

            if torque_cmd == 0:
                bot.Arm.Arm_serial_set_torque(0)
                
            if gripper_cmd is not None:

                angle = int(float(gripper_cmd))
                bot.set_gripper(angle)


            if target_pos is not None:

                if isinstance(target_pos,(list,tuple)):
                    x,y,z = map(float,target_pos)

                elif isinstance(target_pos,dict):
                    x = float(target_pos["x"])
                    y = float(target_pos["y"])
                    z = float(target_pos["z"])

                else:
                    continue
                bot.Arm.Arm_serial_set_torque(1)
                bot.move_to_xyz(x,y,z,duration_ms=1000)


            with shared.state_lock:

                shared.robot_state["x"] = bot.last_pos[0]
                shared.robot_state["y"] = bot.last_pos[1]
                shared.robot_state["z"] = bot.last_pos[2]

                degrees = [math.degrees(rad) for rad in bot.last_joints]

                shared.joints_degrees = degrees[1:6]


            time.sleep(0.05)


    finally:

        if bot is not None:
            bot.go_home()
