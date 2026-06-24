import pybullet as p
import pybullet_data
import time
import numpy as np
import cv2
import math
import shared_data as shared

def run_simulation():
    # ====================================
    # 변수
    # ====================================
    
    # ============ Robot 변수 ============
    arm_joints = [0, 1, 2, 3, 4]
    gripper_joints = [5,6]
    
    # ============ Loop 변수 ============
    SIM_HZ = 240.0
    SIM_DT = 1.0 / SIM_HZ
    CAM_HZ = 30.0    
    CAM_DT = 1.0 / CAM_HZ
    
    last_time = time.time()
    last_cam_time = time.time()
    
    # ============ Object 변수 ============
    urdf_dict = {
        "duck": "duck_vhacd", 
        "soccerball": "soccerball",
        "teddy": "teddy_vhacd",
        "mug": "mug"
    }
    object_id = None
    object_quaternion = p.getQuaternionFromEuler([math.pi/2, 0, math.pi/2]) # 오브젝트 회전 각도
    
    # 투명 발판
    plate_id = None
    no_contact_steps = 0

    
    # ====================================
    # PyBullet 세팅
    # ====================================
    
    # ============ PyBullet 환경 세팅 ============
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.loadURDF("plane.urdf")


    # ============ Robot 세팅 ============
    robot_id = p.loadURDF("dofbot.urdf", basePosition=[0, 0, 0], useFixedBase=True)
    num_joints = p.getNumJoints(robot_id)
    
    # Joint Limit 설정
    joint_limits = []
    for i in range(num_joints):
        info = p.getJointInfo(robot_id, i)
        joint_limits.append((info[8], info[9]))
    
    # End-Effector Index 설정
    for i in range(num_joints):
        if p.getJointInfo(robot_id, i)[12].decode() == "end-effector":
            end_effector_index = i
            break
        
    for finger in (5,6):     
        p.changeDynamics(robot_id, finger,
            lateralFriction=2
        )



    # ============ 카메라 설정 ============
    WIDTH, HEIGHT = 600, 480
    view_matrix = p.computeViewMatrix(
        cameraEyePosition=[0.5, 0, 0.5], # 카메라 위치
        cameraTargetPosition=[0, 0, 0], # 카메라가 바라볼 좌표
        cameraUpVector=[0, 0, 1] # 어디가 위쪽인지 설정
    )
    
    # 카메라 렌즈 설정
    near = 0.01 # (최소) 렌더링 거리
    far = 10.0 # (최대) 렌더링 거리
    
    projection_matrix = p.computeProjectionMatrixFOV(
        60, # 시야각
        float(WIDTH)/HEIGHT, # 가로/세로 비율
        near,
        far
    )

    plate_col = p.createCollisionShape(
        shapeType=p.GEOM_BOX,
        halfExtents=[0.05, 0.05, 0.01]
    )   
                    
    plate_vis = p.createVisualShape(
        shapeType=p.GEOM_BOX,
        halfExtents=[0.05, 0.05, 0.01],
        rgbaColor=[1, 1, 1, 0]
    )


    # ====================================
    # 시뮬레이션 Loop
    # ====================================
    print(">>> PyBullet Simulation Started")

    while True:
        current_time = time.time()
        p.stepSimulation() # 시뮬레이션 스텝 실행

        

        with shared.cmd_lock:
            # ====================================
            # 오브젝트 제어
            # ====================================
            
            # ============ 오브젝트 생성/제거 ============
            if shared.command["object_cmd"]:
                cmd = shared.command["object_cmd"]
                
                # 생성
                if cmd["op"] == "create" and object_id is None:
                    urdf_name = urdf_dict.get(cmd["object"], "duck_vhacd")
                    
                    # 사이즈 설정
                    size = 0.75
                    if urdf_name == "soccerball":
                        size = 0.05
                    elif urdf_name == "mug":
                        size = 0.45
                        
                    # 회전 설정
                    if urdf_name == "mug":
                        object_quaternion = [0,0,0,1]
                    else: object_quaternion = p.getQuaternionFromEuler([math.pi/2, 0, math.pi/2])
                    
                    # 위치 설정
                    base_pos = [0.15,0,0.02]
                    if urdf_name == "teddy_vhacd": 
                        base_pos[1] -= 0.07
                        base_pos[2] -= 0.02
                        
                    # 오브젝트 생성
                    object_id = p.loadURDF(f"{urdf_name}.urdf", basePosition=base_pos, baseOrientation=object_quaternion, globalScaling=size, useFixedBase=False)
                    
                    p.changeDynamics(object_id, -1, lateralFriction=1.2) # 마찰력 설정
                    
                    # 투명 발판 설정
                    if cmd["fix"] == True:
                        plate_id = p.createMultiBody(
                            baseMass=0,
                            baseCollisionShapeIndex=plate_col,
                            baseVisualShapeIndex=plate_vis,
                            basePosition=[0.15, 0, 0.01]
                        )
                    
                    
                # 삭제
                elif cmd["op"] == "delete" and object_id is not None:
                    p.removeBody(object_id)
                    object_id = None
                    if plate_id is not None:
                        p.removeBody(plate_id)  
                        plate_id = None
                    
                shared.command["object_cmd"] = None


            # ============ 오브젝트 위치 제어 ============
            if shared.command["object_pos_cmd"] and object_id is not None:
                object_pos = shared.command["object_pos_cmd"]
                    
                p.resetBasePositionAndOrientation(object_id, object_pos, object_quaternion)
                # 투명 발판 위치 조정
                if plate_id is not None:
                    object_pos[2] -= 0.03
                    p.resetBasePositionAndOrientation(plate_id, shared.command["object_pos_cmd"], [0,0,0,1])
                elif cmd["fix"]:
                    plate_id = p.createMultiBody(
                        baseMass=0,
                        baseCollisionShapeIndex=plate_col,
                        baseVisualShapeIndex=plate_vis,
                        basePosition=object_pos
                    )
                shared.command["object_pos_cmd"] = None
            
            
            # ============ 투명 발판 제거 ============
            if plate_id is not None:
                contacts = p.getContactPoints(
                    bodyA=object_id,
                    bodyB=plate_id
                )
                
                # 60 프레임 이상 오브젝트와 떨어졌을 경우 제거
                no_contact_steps += 1 if len(contacts) == 0 else 0
                if no_contact_steps > 60:
                    p.removeBody(plate_id)  
                    plate_id = None
                    no_contact_steps = 0
            
            
            # ====================================
            # 로봇 동작 수행
            # ====================================

            # ============ 로봇 제어 변수 설정 ============
            target_pos = shared.command["target_pos"] # 목표 좌표
            force = shared.command["force"] # 힘
            max_vel = shared.command["max_velocity"] # 최대 속도
            
            
            # ============ IK 제어 ============
            if target_pos is not None:
                ik_solution = p.calculateInverseKinematics(
                    robot_id, end_effector_index, target_pos,
                    maxNumIterations=200, residualThreshold=1e-4
                )
                for idx, joint_idx in enumerate(arm_joints):
                    lower, upper = joint_limits[joint_idx]
                    angle = max(min(ik_solution[idx], upper), lower)
                    p.setJointMotorControl2(robot_id, joint_idx, p.POSITION_CONTROL, angle, force=force, maxVelocity=max_vel)
                shared.command["target_pos"] = None
                
        
            # ============ Joints 직접 제어 ============
            if shared.command["joint_cmd"]:
                joints_angles = shared.command["joint_cmd"]
                
                # 로봇 제어
                for idx, angle in enumerate(joints_angles):
                    rad_angle = math.radians(angle) # degree -> radian
                    
                    p.setJointMotorControl2(
                        robot_id, 
                        arm_joints[idx], 
                        p.POSITION_CONTROL, 
                        rad_angle, 
                        force=force, 
                        maxVelocity=max_vel
                    )
                
                shared.command["joint_cmd"] = None
                
                
            # ============ Gripper 제어 ============
            if shared.command["gripper_cmd"] is not None:
                gripper_value = math.floor((shared.command["gripper_cmd"]/2) * 1000) / 1000 # 0.8 -> 0.3, 0.3로 각 손가락에 전달
                for finger in gripper_joints:
                    p.setJointMotorControl2(
                        robot_id, 
                        finger, 
                        p.POSITION_CONTROL, 
                        gripper_value, 
                        force=force, 
                        maxVelocity=max_vel * 0.08 # Gripper 속도 보정
                    )
                
                shared.command["gripper_cmd"] = None
        
        

        # ====================================
        # 데이터 업데이트
        # ====================================
        
        # ============ End-Effector ============
        ee_pos = p.getLinkState(robot_id, end_effector_index)[0]
        
        # ============ Joints ============
        joints = [round(np.degrees(p.getJointState(robot_id, j)[0]), 2) for j in arm_joints]

        # ============ gripper ============
        gripper_state = [p.getJointState(robot_id, j)[0] for j in gripper_joints]

        # ============ Object Info ============
        obj_data = {"exists": False, "x": 0, "y": 0, "z": 0, "distance": 0}
        if object_id:
            pos = p.getBasePositionAndOrientation(object_id)[0]
            dist = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)
            obj_data = {
                "exists": True,
                "x": round(pos[0], 4), "y": round(pos[1], 4), "z": round(pos[2], 4),
                "distance": round(dist, 4)
            }

        # ============ 공유 데이터 업데이트 ============
        with shared.state_lock:
            shared.robot_state["x"] = round(ee_pos[0], 4)
            shared.robot_state["y"] = round(ee_pos[1], 4)
            shared.robot_state["z"] = round(ee_pos[2], 4)
            shared.joints_degrees = joints
            shared.gripper_state = round(sum(gripper_state),4)
            shared.object_info = obj_data



        # ====================================
        # 카메라 업데이트
        # ====================================
        # ============ 카메라 업데이트 ============
        if current_time - last_cam_time >= CAM_DT:
            img = p.getCameraImage(WIDTH, HEIGHT, view_matrix, projection_matrix, renderer=p.ER_BULLET_HARDWARE_OPENGL)
            w, h, rgb, depth, seg = img
            
            # RGB 이미지
            rgb = np.reshape(rgb, (h, w, 4))[:, :, :3].astype(np.uint8)
            
            # Depth RAW 데이터
            depth_buffer = np.reshape(depth, (h, w))
            depth_m = far * near / (far - (far - near) * depth_buffer) # 실제 거리로 변환


            # ============ 엔드 이펙터 View ============
            link_state = p.getLinkState(robot_id, end_effector_index)

            cam_pos = link_state[0]      # position
            cam_ori = link_state[1]      # quaternion

            rot = p.getMatrixFromQuaternion(cam_ori)
            rot = np.array(rot).reshape(3, 3)

            forward = rot @ np.array([0, 0, 1])   # z축 기준
            up = rot @ np.array([-1, 0, 0])

            ee_view_matrix = p.computeViewMatrix(
                cam_pos,
                cam_pos + 0.2 * forward,
                up
            )
            ee_img = p.getCameraImage(WIDTH, HEIGHT, ee_view_matrix, projection_matrix, renderer=p.ER_BULLET_HARDWARE_OPENGL)
            ee_w, ee_h, ee_rgb, ee_depth, seg = ee_img
            
            # RGB 이미지
            ee_rgb = np.reshape(ee_rgb, (ee_h, ee_w, 4))[:, :, :3].astype(np.uint8)
            
            # Depth RAW 데이터
            ee_depth_buffer = np.reshape(ee_depth, (ee_h, ee_w))
            ee_depth_m = far * near / (far - (far - near) * ee_depth_buffer) # 실제 거리로 변환

            
            # 이미지 업데이트
            with shared.frame_lock:
                shared.latest_frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                shared.latest_frame_depth = depth_m
                shared.latest_ee_frame = cv2.cvtColor(ee_rgb, cv2.COLOR_RGB2BGR)
                shared.latest_ee_frame_depth = ee_depth_m
            
            last_cam_time = current_time
            
            
            
        # ====================================
        # 시간 동기화
        # ====================================
        elapsed = time.time() - last_time
        if elapsed < SIM_DT:
            time.sleep(SIM_DT - elapsed)
        last_time = time.time()