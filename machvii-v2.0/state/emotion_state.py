from dataclasses import dataclass, field, asdict
from typing import Dict

@dataclass
class EmotionVector:
    """
    로봇의 감정 상태를 5차원 벡터로 표현합니다. (Modified PAD Model)
    각 값은 0.0 ~ 1.0 사이의 강도를 가집니다.
    """
    # [Focus / Arousal] 주의 집중도 및 각성 수준
    # 1.0: 초집중, 놀람 (High Arousal) | 0.0: 멍함, 지루함 (Low Arousal)
    focus: float = 0.1
    
    # [Effort / Energy] 신체적/정신적 에너지 소모량
    # 1.0: 고부하, 피곤, 힘씀 | 0.0: 편안함, 휴식
    effort: float = 0.0
    
    # [Confidence / Dominance] 상황 통제력 및 성공 확신
    # 1.0: 위풍당당, 환희, 확신 | 0.0: 위축, 공포, 부끄러움
    confidence: float = 0.1
    
    # [Frustration / Distress] 기대와 결과의 불일치, 장애물
    # 1.0: 격분, 짜증, 좌절 | 0.0: 만족, 흐름이 좋음
    frustration: float = 0.0
    
    # [Curiosity / Interest] 새로운 자극에 대한 탐구욕
    # 1.0: 흥미진진, 장난기 | 0.0: 무관심
    curiosity: float = 0.1

    def update(self, delta: Dict[str, float]):
        """델타 업데이트를 안전하게 적용합니다."""
        for key, value in delta.items():
            if hasattr(self, key):
                current = getattr(self, key)
                new_val = max(0.0, min(1.0, current + value))
                setattr(self, key, new_val)
    
    def to_dict(self):
        return asdict(self)
