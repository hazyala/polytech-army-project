import threading
import time
import asyncio
import uuid
from typing import Dict
import os
import re
from shared.config import PathConfig
from state.emotion_state import EmotionVector
from shared.state_broadcaster import broadcaster

class EmotionController:
    """
    현재 감정 벡터를 목표 벡터로 부드럽게 보간(Interpolate)하는 고속 컨트롤러입니다.
    StateBroadcaster를 구독하여 주요 상태 변화에 반응합니다.
    """
    # [Configuration] 16종 프리셋에 대한 목표 벡터 정의
    # 초기에는 비어있으며, frontend/expressions.js를 파싱하여 채웁니다.
    PRESET_VECTORS = {}

    def __init__(self):
        self.current_vector = EmotionVector()
        self.target_vector = EmotionVector()
        self.running = False
        self._lock = threading.RLock()
        
        # JS 파일로부터 프리셋 로드 (Single Source of Truth)
        self._load_presets_from_js()
        
        # 우선순위 제어를 위한 타임스탬프 (파이프라인 업데이트 보호용)
        self.manual_override_until = 0.0
        
        self.last_preset_id = "neutral"
        self.current_preset_id = "neutral" # Brain이 결정한 현재 프리셋
        self.muscles = {}
        
        # Heartbeat 타이머
        self.last_heartbeat_time = 0.0
        
        # 브레인 이벤트 구독 (이제 EmotionBrain이 직접 set_target_preset을 호출)
        # broadcaster.subscribe(self.on_brain_state_change) # Removed as per new architecture

    def _load_presets_from_js(self):
        """
        [Dynamic Loader] frontend/src/constants/expressions.js 파일을 파싱하여
        Emotion Vector 정의를 동적으로 가져옵니다.
        """
        
        js_path = os.path.join(PathConfig.BASE_DIR, "interface", "frontend", "src", "constants", "expressions.js")
        
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Regex to find id and vector block
            # Matches: id: "happy", ... vector: { focus: 0.5, ... }
            # Note: This regex assumes 'id' comes before 'vector' in the object definition
            # or we iterate over objects.
            
            # Strategy: Split by "{" to iterate objects? No, too risky.
            # Strategy: Regex for `id:\s*["'](\w+)["']` ... `vector:\s*\{([^}]+)\}`
            # This assumes vector block is valid and doesn't contain nested braces (it doesn't).
            
            # Let's find all objects roughly.
            # Or just search for the specific pattern sequence.
            pattern = re.compile(r'id:\s*["\'](\w+)["\'][\s\S]*?vector:\s*\{([^}]+)\}')
            
            matches = pattern.findall(content)
            
            count = 0
            for preset_id, vector_str in matches:
                # vector_str example: "focus: 0.1, effort: 0.1, ..."
                vector_data = {}
                
                # Parse key-value pairs
                # key: value (comma or newline or space)
                kv_pattern = re.compile(r'(\w+):\s*([0-9.]+)')
                kv_matches = kv_pattern.findall(vector_str)
                
                for key, val in kv_matches:
                    vector_data[key] = float(val)
                
                self.PRESET_VECTORS[preset_id.lower()] = vector_data
                count += 1
                
            print(f"[EmotionController] Loaded {count} presets from expressions.js")
            # print(f"Loaded keys: {list(self.PRESET_VECTORS.keys())}")
            
        except Exception as e:
            print(f"[EmotionController] ❌ Failed to load expressions.js: {e}")
            # Fallback (Empty, will warn on usage)

    def on_brain_state_change(self, state: Dict[str, any]):
        """
        [Architecture Change] 
        이제 EmotionController는 독자적으로 판단하지 않습니다. 
        BrainState 변화에 따른 감정 결정은 EmotionBrain이 전담합니다.
        """
        pass

    def update_target(self, new_target: Dict[str, float], duration: float = 3.0):
        """
        [Legacy Support] 직접 벡터 제어가 필요한 특수 경우를 위해 유지
        """
        # [Debug] 외부 타겟 업데이트 로그
        # print(f"[Emotion DEBUG] update_target called: {new_target}")
        
        with self._lock:
            self.manual_override_until = time.time() + duration
            for k, v in new_target.items():
                if hasattr(self.target_vector, k):
                    setattr(self.target_vector, k, v)

    def set_target_preset(self, preset_id: str):
        """
        [Main Interface] EmotionBrain이 호출하는 메인 함수.
        특정 프리셋으로 목표를 설정합니다.
        """
        preset_id = preset_id.lower()
        
        # [Fallback] 매핑되지 않은 키 처리
        if preset_id not in self.PRESET_VECTORS:
            # 주요 LLM 환각 키에 대한 매핑
            mapping = {
                "proud": "joy",
                "smile": "happy",
                "laugh": "joy",
                "cry": "sad",
                "worried": "suspicious",
                "love": "shy",
                "scared": "fear"
            }
            if preset_id in mapping:
                preset_id = mapping[preset_id]
            else:
                print(f"[Emotion] Warning: Unknown preset '{preset_id}'. Ignoring.")
                return

        with self._lock:
            # 1. 프리셋 즉시 변경 (Brain의 결정이므로 즉시 반영)
            self.current_preset_id = preset_id 
            
            # 2. 목표 벡터 설정
            target_vals = self.PRESET_VECTORS[preset_id]
            for k, v in target_vals.items():
                if hasattr(self.target_vector, k):
                    setattr(self.target_vector, k, v)
            
            # print(f"[Emotion] Set Target: {preset_id.upper()}")

    def broadcast_emotion_event(self, preset_id: str, weight: float = 1.0, duration: float = 3.0):
        """
        [Emotion Pulse] 프론트엔드 동기화용 (강제 이벤트)
        """
        # [Fix] 유실 방지 Event Buffer
        broadcaster.publish_event("emotion_pulse", {
            "preset": preset_id,
            "weight": weight,
            "duration": duration
        })

    def step(self, dt: float):
        """현재 상태를 목표 상태로 보간하고 상태 유지를 위한 Heartbeat를 쏩니다."""
        smoothing_factor = 3.0 * dt # 반응 속도 상향 (Overhaul)
        
        with self._lock:
            # [Advanced Logic] 시간에 따른 상태 변화 (Drift) - Moved to Brain
            # self._apply_temporal_drift(dt)
            
            curr = self.current_vector
            tgt = self.target_vector
            
            # 1. 감정 벡터 보간 (Lerp)
            curr.focus += (tgt.focus - curr.focus) * smoothing_factor
            curr.effort += (tgt.effort - curr.effort) * smoothing_factor
            curr.confidence += (tgt.confidence - curr.confidence) * smoothing_factor
            curr.frustration += (tgt.frustration - curr.frustration) * smoothing_factor
            curr.curiosity += (tgt.curiosity - curr.curiosity) * smoothing_factor

            # 2. SystemState 동기화
            from state.system_state import system_state
            system_state.emotion.focus = curr.focus
            system_state.emotion.effort = curr.effort
            system_state.emotion.confidence = curr.confidence
            system_state.emotion.frustration = curr.frustration
            system_state.emotion.curiosity = curr.curiosity
            
            # [Centralized] 현재 프리셋은 Brain이 정해준 값 (`self.current_preset_id`)
            # 별도의 get_closest_preset 로직을 거치지 않음
            active_preset = self.current_preset_id
            
        # --- LOCK RELEASED ---
        
        # 3. 프리셋 변경 감지 및 브로드캐스트
        if active_preset != self.last_preset_id:
            print(f"[Emotion] State Transition: {self.last_preset_id.upper()} -> {active_preset.upper()}")
            self.last_preset_id = active_preset
            self.broadcast_emotion_event(active_preset, weight=1.0, duration=5.0)
                 
        # 4. Heartbeat (프론트엔드 동기화 유지)
        now = time.time()
        if now - self.last_heartbeat_time > 1.0:
            broadcaster.publish_event("emotion_pulse", {
                "preset": active_preset,
                "weight": 1.0,
                "duration": 2.0
            })
            self.last_heartbeat_time = now

    # [Deleted] _apply_temporal_drift (Moved to Brain)

    # [Deleted] get_closest_preset (Deprecated)
    def get_closest_preset(self) -> str:
        """
        [Deprecated] 이제 EmotionBrain이 프리셋을 직접 결정합니다.
        """
        return self.current_preset_id

    def _check_preset_change(self):
            vec = self.current_vector
            print(f"[Emotion] Vector State Changed: {self.last_preset_id.upper()} -> {new_preset.upper()}")
            
            self.last_preset_id = new_preset
            
            if new_preset != 'neutral':
                 self.broadcast_emotion_event(new_preset, weight=1.0, duration=5.0)

    def start(self):
        """60Hz 보간 루프를 시작합니다."""
        if self.running: return
        self.running = True
        self.muscles = {} 
        self.last_preset_id = "neutral"
        self.current_preset_id = "neutral" # [New] Brain이 제어하는 현재 프리셋 ID
        self.current_brain_state = "IDLE" # 초기화
        
        # [Fix] 시작 시 강제로 IDLE Target 셋팅하여 초기값 불일치 방지
        self.target_vector.focus = 0.25
        self.target_vector.effort = 0.2
        self.target_vector.frustration = 0.0
        self.target_vector.confidence = 0.3
        self.target_vector.curiosity = 0.1
        
        # Current도 초기화
        self.current_vector.focus = 0.25
        self.current_vector.effort = 0.2
        self.current_vector.frustration = 0.0
        self.current_vector.confidence = 0.3
        self.current_vector.curiosity = 0.1
        
        self.state_enter_time = time.time()
        
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[Emotion] 컨트롤러 시작됨 (60Hz).")

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
            
    def _loop(self):
        last_time = time.time()
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            self.step(dt)
            
            # 약 60Hz 유지
            time.sleep(max(0, 1/60.0 - (time.time() - current_time)))

    def get_current_emotion(self):
        with self._lock:
            preset = self.get_closest_preset()
            return {
                "vector": self.current_vector.to_dict(),
                "preset_id": preset,
                "muscles": {}
            }

# 싱글톤 인스턴스
emotion_controller = EmotionController()
