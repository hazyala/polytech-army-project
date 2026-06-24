import time
import math
import os
from Arm_Lib import Arm_Device
import ikpy.chain


class DofbotSimple:

    def __init__(self, urdf_file_name):
        self.Arm = Arm_Device()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        urdf_path = os.path.join(current_dir, urdf_file_name)

        self.chain = ikpy.chain.Chain.from_urdf_file(
            urdf_path,
            active_links_mask=[False, True, True, True, True, True, False]
        )

        self.gripper_angle = 90
        self.last_pos = [0.0, 0.0, 0.0]
        self.last_joints = [0.0] * 7

    def set_gripper(self, angle, duration_ms=1500):
        angle = int(max(10, min(170, angle)))

        if self.gripper_angle == angle:
            return

        self.gripper_angle = angle

        self.Arm.Arm_serial_servo_write(
            6,
            angle,
            int(duration_ms)
        )

    def move_to_xyz(self, x, y, z, duration_ms=1500):

        target_position = [x, y, z]

        ik_angles = self.chain.inverse_kinematics(
            target_position,
            orientation_mode=None
        )

        self.last_joints = ik_angles
        self.last_pos = [x, y, z]

        s1 = 90 + math.degrees(ik_angles[1])
        s2 = 90 + math.degrees(ik_angles[2])
        s3 = 90 + math.degrees(ik_angles[3])
        s4 = 90 + math.degrees(ik_angles[4])
        s5 = 90

        safe = [int(max(0, min(180, a))) for a in [s1, s2, s3, s4, s5]]

        self.Arm.Arm_serial_servo_write6(
            safe[0],
            safe[1],
            safe[2],
            safe[3],
            safe[4],
            self.gripper_angle,
            int(duration_ms)
        )

    def go_home(self):

        self.Arm.Arm_serial_servo_write6(
            90,
            90,
            90,
            90,
            90,
            self.gripper_angle,
            1000
        )

        time.sleep(1.5)

        self.last_pos = [0.0, 0.0, 0.0]
        self.last_joints = [0.0] * 7
