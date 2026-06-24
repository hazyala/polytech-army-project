import time
import threading
from typing import Dict

from state.system_state import system_state
from expression.emotion_controller import emotion_controller
from shared.state_broadcaster import broadcaster

class EmotionBrain:
    """
    [Central Emotion Unit]
    시스템 전체의 상태(SystemState)를 종합적으로 판단하여 
    로봇의 감정 표정(Preset)을 결정하는 최상위 의사결정 모듈입니다.
    
    기존의 분산된 감정 로직(VisualServoing에서 직접 호출 등)을 대체하며,
    규칙(Rule) 기반으로 명확한 인과관계를 가집니다.
    """
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_action_time = time.time()
        self.lock = threading.RLock()
        
        # 이전 상태 추적용 (변화 감지)
        self.last_arm_status = "IDLE"
        self.last_agent_state = "IDLE"
        
        # [Chat Emotion] 대화에서 발생한 감정 오버라이드 (지속성)
        self.context_emotion = "neutral"

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[EmotionBrain] 중앙 감정 제어 장치 가동됨.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def set_emotional_override(self, preset_id: str, duration: float = None):
        """
        대화(LLM) 등에서 감정 표현을 요청할 때 사용
        Note: duration은 하위 호환성을 위해 남겨두지만, 실제로는 무시되고 다음 입력/Boredom까지 지속됩니다.
        """
        with self.lock:
            self.context_emotion = preset_id
            self.last_action_time = time.time() # 감정 변화도 '활동'으로 간주하여 지루함 타이머 리셋
            # print(f"[EmotionBrain] Context Emotion Set: {preset_id} (Persistent)")
            
    def _loop(self):
        while self.running:
            time.sleep(0.5) # 2Hz Update
            self._update_emotion()

    def _update_emotion(self):
        # 1. 상태 수집
        arm_status = system_state.robot.arm_status 
        
        # [Fix] Broadcaster에서 직접 Agent State(THINKING/IDLE) 조회
        # EmotionController가 아닌 Broadcaster가 진실의 원천임
        context = broadcaster.get_snapshot()
        agent_state = context.get("agent_state", "IDLE") 
        
        # 2. 활동 시간 추적 (IDLE Timeout 판별용)
        is_active = (arm_status != "IDLE") or (agent_state != "IDLE")
        if is_active:
            with self.lock:
                self.last_action_time = time.time()
                
        # 3. 우선순위 기반 감정 결정 (Decision Tree)
        target_preset = "neutral"
        
        # Priority 1: Physical Execution (몸을 쓸 때는 안전을 위해 집중)
        if arm_status in ["VISUAL_SERVO", "APPROACH", "GRASP", "SEARCH"]:
            target_preset = "focused"
            
        # Priority 2: Execution Result (동작 직후 결과 반응 & 지속 상태 업데이트)
        elif arm_status == "SUCCESS":
            target_preset = "joy"
            # [New] 행동의 결과가 곧 나의 새로운 기분(Context)이 된다.
            with self.lock:
                self.context_emotion = "joy"
                self.last_action_time = time.time()
                
        elif arm_status == "FAIL":
            target_preset = "sad"
            # [New] 행동의 결과가 곧 나의 새로운 기분(Context)이 된다.
            with self.lock:
                self.context_emotion = "sad"
                self.last_action_time = time.time()
                
        elif arm_status == "LOST":
            target_preset = "confused"
            # [New] 잠깐 놓친 것은 문맥을 해치지 않으므로 Context 저장은 생략하거나, 
            # 필요 시 "neutral"로 리셋할 수 있음. 여기선 즉각 반응만 함.
        
        # Priority 3: Mental State (생각 중 - 대화 감정보다 우선하여 '생각하는 표정' 노출)
        elif agent_state == "PLANNING" or agent_state == "THINKING":
            target_preset = "thinking"
            
        # Priority 4: Idle & Boredom & Context
        else: # IDLE
            elapsed = time.time() - self.last_action_time
            if elapsed > 600.0: # 10분
                target_preset = "bored"
            else:
                # 아무것도 안 할 때는 '최근 대화 감정'을 유지
                target_preset = self.context_emotion
                
        # 4. 명령 하달
        if target_preset != emotion_controller.current_preset_id:
            # [DEBUG] 감정 변화 추적
            print(f"[EmotionBrain DEBUG] Changing: {emotion_controller.current_preset_id} -> {target_preset}")
            print(f"   Reason: Arm={arm_status}, Agent={agent_state}, Context={self.context_emotion}, Elapsed={time.time()-self.last_action_time:.1f}s")
            
            emotion_controller.set_target_preset(target_preset)

# 싱글톤 인스턴스
emotion_brain = EmotionBrain()
