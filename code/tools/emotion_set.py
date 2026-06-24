import streamlit as st
import json
import re
import sys
import os

# [중요] face_renderer를 임포트하기 위해 경로를 추가합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # code 폴더
sys.path.append(parent_dir)

from face_renderer import render_face_svg
from langchain.tools import tool
from logger import get_logger

logger = get_logger('TOOLS')

# 인사이드 아웃 감정 프리셋
EMOTION_PRESETS = {
    'idle':          {'eye': 100, 'mouth': 0,   'color': '#FFFFFF'},
    'thinking':      {'eye': 60,  'mouth': 10,  'color': '#B0C4DE'},
    'joy':           {'eye': 95,  'mouth': 40,  'color': '#FFD700'},
    'sadness':       {'eye': 40,  'mouth': -60, 'color': '#4169E1'},
    'anger':         {'eye': 70,  'mouth': -50, 'color': '#FF0000'},
    'disgust':       {'eye': 60,  'mouth': -30, 'color': '#32CD32'},
    'fear':          {'eye': 100, 'mouth': -10, 'color': '#9370DB'},
    'anxiety':       {'eye': 85,  'mouth': -20, 'color': '#FF8C00'},
    'embarrassment': {'eye': 50,  'mouth': -10, 'color': '#FF69B4'},
    'envy':          {'eye': 90,  'mouth': 40,  'color': '#00CED1'},
    'ennui':         {'eye': 30,  'mouth': 0,   'color': '#483D8B'},
}

KOREAN_MAPPING = {
    '기쁨': 'joy', '슬픔': 'sadness', '버럭': 'anger', '화남': 'anger',
    '까칠': 'disgust', '소심': 'fear', '불안': 'anxiety', 
    '당황': 'embarrassment', '부럽': 'envy', '따분': 'ennui',
    '생각': 'thinking', '대기': 'idle'
}

@tool
def emotion_set(emotion_input: str) -> str:
    """
    Sets the robot's facial expression.
    Supports JSON input (preferred) or keywords (e.g., 'joy', 'anxiety').
    Updates the face visibly in REAL-TIME.
    """
    try:
        clean_input = emotion_input.strip()
        new_params = {}
        target_preset_name = "CUSTOM"

        # [1단계] JSON 파싱 시도 (가장 정확함)
        # 에이전트가 {"eye": 100...} 형태로 보낼 때 완벽하게 처리
        try:
            # 혹시 모를 작은따옴표 처리
            if "'" in clean_input and '"' not in clean_input:
                clean_input = clean_input.replace("'", '"')
            
            # JSON 파싱
            if "{" in clean_input:
                # 중괄호 부분만 추출 시도 (앞뒤 잡다한 텍스트 제거)
                start = clean_input.find("{")
                end = clean_input.rfind("}") + 1
                json_str = clean_input[start:end]
                new_params = json.loads(json_str)
                logger.info(f"JSON Parsed: {new_params}")
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}. Trying keywords/regex.")
        
        # [2단계] JSON 실패 시 키워드/Regex 파싱
        if not new_params:
            lower_input = clean_input.lower()
            # 키워드 매칭
            keyword = re.sub(r'[^a-z0-9]', '', lower_input)
            
            # 한글/영어 매핑 확인
            found_key = None
            if keyword in EMOTION_PRESETS:
                found_key = keyword
            else:
                for kr, en in KOREAN_MAPPING.items():
                    if kr in lower_input:
                        found_key = en
                        break
            
            if found_key:
                new_params = EMOTION_PRESETS[found_key].copy()
                target_preset_name = found_key.upper()
            else:
                # 최후의 수단: Regex로 숫자와 색상 추출
                eye = re.search(r'eye\D*(\d+)', lower_input)
                if eye: new_params['eye'] = int(eye.group(1))
                
                mouth = re.search(r'mouth\D*(-?\d+)', lower_input)
                if mouth: new_params['mouth'] = int(mouth.group(1))
                
                # [수정] 색상 코드 파싱 개선 (이전의 'd' 오류 수정)
                # # 뒤에 6자리 16진수 혹은 영단어
                color = re.search(r'color\D*(#[0-9a-fA-F]{6}|[a-z]+)', lower_input)
                if color: new_params['color'] = color.group(1)

        if not new_params:
            return "감정 설정 실패: 입력값을 이해할 수 없습니다."

        # 3. 세션 상태 업데이트
        current = st.session_state.get('face_params', EMOTION_PRESETS['idle'].copy())
        current.update(new_params)
        st.session_state.face_params = current
        st.session_state.current_emotion = target_preset_name

        # [핵심] 실시간 UI 업데이트 (즉시 반영)
        # main.py에서 공유해준 'face_container'가 있다면 바로 그립니다.
        if "face_container" in st.session_state:
            container = st.session_state.face_container
            # SVG 생성
            raw_svg = render_face_svg(
                eye_openness=current.get("eye", 100),
                mouth_curve=current.get("mouth", 0),
                eye_color=current.get("color", "#FFFFFF")
            )
            clean_svg = " ".join(raw_svg.split())
            container.markdown(f'<div class="face-card">{clean_svg}</div>', unsafe_allow_html=True)

        return f"Face updated to: {new_params}"

    except Exception as error:
        logger.error(f"Error in emotion_set: {error}")
        return f"Failed to set emotion: {str(error)}"