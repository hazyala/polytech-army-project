import logging
import re
import time
from shared.state_broadcaster import broadcaster
from strategy.visual_servoing import visual_servoing
from embodiment.robot_controller import robot_controller

class ActionDispatcher:
    """
    [Layer 4: Strategy Dispatcher]
    Brain의 추상적인 의도(Intent)를 구체적인 행동 전략(Strategy)이나
    단순 하드웨어 명령(Embodiment)으로 변환하여 전달하는 중추 신경계입니다.

    기존 RobotController에 있던 파싱 및 분기 로직을 이곳으로 이관하여
    'Embodiment'가 'Strategy'를 모르게 하는 정방향 아키텍처를 완성합니다.
    """
    def __init__(self):
        logging.info("[ActionDispatcher] 초기화 중... Broadcaster 구독 시작")
        self.last_action_intent = None
        self.last_grasp_timestamp = 0.0
        broadcaster.subscribe(self.on_intent_received)

    def on_intent_received(self, data: dict):
        """
        Broadcaster로부터 action_intent 또는 grasp_intent를 수신합니다.
        """
        # 1. Action Intent (Natural Language -> Pipeline)
        intent = data.get("action_intent")
        if intent and intent != self.last_action_intent:
            self.last_action_intent = intent
            self._handle_action_intent(intent)

        # 2. Grasp Intent (Tool -> Strategy)
        grasp_data = data.get("grasp_intent")
        if grasp_data:
            timestamp = grasp_data.get("timestamp", 0)
            if timestamp > self.last_grasp_timestamp:
                self.last_grasp_timestamp = timestamp
                target = grasp_data.get("target_name", "Object")
                logging.info(f"[ActionDispatcher] Grasp Intent 수신: {target}")
                self._dispatch_grasp_strategy(target_label=target)

    def _handle_action_intent(self, intent: str):
        logging.info(f"[ActionDispatcher] 의도 수신: {intent}")
        intent_lower = intent.lower()

        # 1. [Strategy] 복합 행동: 잡기 (Pick/Grasp)
        if any(k in intent_lower for k in ["잡아", "집어", "pick", "grab"]):
            self._dispatch_grasp_strategy(intent_str=intent_lower)

        # 2. [Embodiment] 단순 행동: 인사 (Greet)
        elif any(k in intent_lower for k in ["인사", "반가워", "hello", "greet", "안녕"]):
            self._dispatch_greet()

        # 3. [Embodiment] 단순 행동: 들어올리기 (Lift)
        elif any(k in intent_lower for k in ["들어", "lift", "올려"]):
            self._dispatch_lift()

        # 4. [Embodiment] 원시 이동 (Relative Move)
        elif self._dispatch_relative_move(intent_lower):
            pass 

        # 5. [Embodiment] 그리퍼 제어
        elif self._dispatch_gripper(intent_lower):
            pass

        # 6. [Embodiment] 정지 (Stop)
        elif any(k in intent_lower for k in ["멈춰", "정지", "stop"]):
            robot_controller.stop()

        else:
            logging.info(f"[ActionDispatcher] 처리되지 않은 의도: {intent}")

    def _dispatch_grasp_strategy(self, intent_str: str = None, target_label: str = None):
        """
        '잡기' 전략 실행.
        intent_str(자연어) 또는 target_label(직접 지정) 중 하나를 사용.
        """
        from state.system_state import system_state
        
        # 1. 타겟 결정
        final_label = target_label
        
        if not final_label and intent_str:
            # 자연어에서 추론 불가능하면 시야의 첫번째 물체
            perception = system_state.perception_data
            objects = perception.get("detected_objects", [])
            if not objects:
                broadcaster.publish("agent_thought", "[Dispatcher] 시야에 물체가 없어 제자리 대기합니다.")
                return
            final_label = objects[0].get("label", "Object")
        
        if not final_label:
            logging.warning("[Dispatcher] 잡기 대상이 지정되지 않았습니다.")
            return

        broadcaster.publish("agent_thought", f"[Dispatcher] '{final_label}' 파지 전략(VisualServoing)을 가동합니다.")
        
        # VisualServoing에게 위임
        success = visual_servoing.execute_approach_and_grasp(target_label=final_label)
        
        if success:
            broadcaster.publish("agent_thought", f"[Dispatcher] '{final_label}' 공략 완료. 다음 지시를 기다립니다.")
        else:
            broadcaster.publish("agent_thought", f"[Dispatcher] '{final_label}' 공략 실패.")

    def _dispatch_greet(self):
        """
        [Strategy] 전신 인사 (Coordinate Control + Joint Control)
        손을 흔드는 동작은 move_to_xyz를 사용하고,
        기본 자세 복귀는 set_joints를 사용하여 명시적으로 수직 일직선 자세를 만듭니다.
        """
        broadcaster.publish("agent_thought", "[Dispatcher] 반갑게 인사를 건넵니다.")
        
        try:
            # 기본 자세 정의 (xyz 좌표)
            BASE_X = 25.0  # cm
            BASE_Y = 0.0   # cm (중앙)
            
            # 수직 일직선 기본 자세 (관절각, degrees)
            # 실제 로봇에서 수동으로 수직 자세를 만들고 측정한 값
            # 위치: x=25, y=0, z=25 (cm)
            BASE_JOINTS = [0, -21, -3, -72, 0]
            
            # 1. 안녕 동작 수행 (xyz 좌표 사용)
            greet_z = 25.0
            
            # 2. 손 흔들기 (Y축 좌우)
            for _ in range(2):
                # Left
                robot_controller.robot_driver.move_to_xyz(BASE_X, BASE_Y + 5.0, greet_z)
                time.sleep(0.8)
                # Right
                robot_controller.robot_driver.move_to_xyz(BASE_X, BASE_Y - 5.0, greet_z)
                time.sleep(0.8)
            
            # 3. 중앙 복귀
            robot_controller.robot_driver.move_to_xyz(BASE_X, BASE_Y, greet_z)
            time.sleep(1.0)
            
            # 4. 기본 자세로 복귀 (관절각 사용 - 수직 일직선)
            logging.info(f"[Dispatcher] 기본 자세 복귀: {BASE_JOINTS}")
            robot_controller.robot_driver.set_joints(BASE_JOINTS)
            time.sleep(1.5)
            
            broadcaster.publish("agent_thought", "[Dispatcher] 인사를 마치고 기본 자세로 돌아왔습니다.")

        except Exception as e:
            logging.error(f"[Dispatcher] 인사 동작 실패: {e}")

    def _dispatch_lift(self):
        """들어올리기 동작"""
        broadcaster.publish("agent_thought", "[Dispatcher] 물체를 들어올립니다.")
        current_pose = robot_controller.robot_driver.get_current_pose()
        # [Fix] get_current_pose()는 {'position': {'x','y','z'}} 구조를 반환함
        pos = current_pose['position']
        target_z = pos['z'] + 15.0
        robot_controller.robot_driver.move_to_xyz(pos['x'], pos['y'], target_z)

    def _dispatch_relative_move(self, intent: str) -> bool:
        """상대 좌표 이동 파싱 및 디스패치"""
        dx, dy, dz = 0.0, 0.0, 0.0
        processed = False
        
        if "왼쪽" in intent or "left" in intent: dy = 5.0; processed = True
        if "오른쪽" in intent or "right" in intent: dy = -5.0; processed = True
        if "위" in intent or "up" in intent: dz = 5.0; processed = True
        if "아래" in intent or "down" in intent: dz = -5.0; processed = True
        if "앞" in intent or "front" in intent: dx = 5.0; processed = True
        if "뒤" in intent or "back" in intent: dx = -5.0; processed = True
            
        match = re.search(r'(\d+(?:\.\d+)?)', intent)
        if match:
            val = float(match.group(1))
            val = min(20.0, max(1.0, val))
            if dx != 0: dx = val if dx > 0 else -val
            if dy != 0: dy = val if dy > 0 else -val
            if dz != 0: dz = val if dz > 0 else -val
            
        if processed:
            broadcaster.publish("agent_thought", f"[Dispatcher] 상대 이동 지시: {dx}, {dy}, {dz}")
            cur = robot_controller.robot_driver.get_current_pose()
            # [Fix] get_current_pose()는 {'position': {'x','y','z'}} 구조를 반환함
            pos = cur['position']
            robot_controller.robot_driver.move_to_xyz(pos['x']+dx, pos['y']+dy, pos['z']+dz)
            return True
        return False

    def _dispatch_gripper(self, intent: str) -> bool:
        """그리퍼 제어 파싱 및 디스패치"""
        val = None
        if any(k in intent for k in ["열어", "open"]): val = 100
        elif any(k in intent for k in ["잡아", "닫아", "close"]): val = 0
        
        if val is not None:
            broadcaster.publish("agent_thought", f"[Dispatcher] 그리퍼 제어: {val}")
            robot_controller.robot_driver.move_gripper(val)
            return True
        return False

# 싱글톤 인스턴스
action_dispatcher = ActionDispatcher()
