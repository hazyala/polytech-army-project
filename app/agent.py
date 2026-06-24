# app/agent.py

import streamlit as st
import cv2
import base64
import os
from langchain_community.chat_models import ChatOllama
from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool

# ==========================================
# 0. 모델 주소(Path) 설정 (여기서 모델 이름과 주소를 관리합니다)
# ==========================================

# 👁️ 눈 (비전 모델): 로컬에 있는 가볍고 빠른 모델 (이미지 분석용)
VISION_MODEL_URL = "http://host.docker.internal:11434"
VISION_MODEL_NAME = "gemma3:4b"  

# 🧠 뇌 (대화 모델): 성능 좋은 똑똑한 모델 (판단 및 추론용)
BRAIN_MODEL_URL = "http://ollama.aikopo.net" 
BRAIN_MODEL_NAME = "gemma3:27b"

# ==========================================
# 1. 도구 정의 (Tools)
# ==========================================

@tool
def look_at_camera(query: str) -> str:
    """
    [Basic Vision] The PRIMARY source for vision. ALWAYS use this tool FIRST.
    It returns a list of detected objects (e.g., 'person, cup') from YOLO (Text only).
    Use this for general queries like "What is in front of me?", "Is there a person?", "Auto-check".
    """
    if "last_vision_result" in st.session_state:
        # 젬마가 헷갈리지 않게 'Text Only'임을 강조
        return f"Detected Objects (YOLO Text): {st.session_state.last_vision_result}"
    return "Nothing detected."

@tool
def analyze_current_scene(query: str) -> str:
    """
    [Advanced Vision] A HEAVY and SLOW tool. Use this ONLY when the user EXPLICITLY asks for visual details 
    that simple object detection cannot provide (e.g., "What color is the shirt?", "What is the person doing?").
    
    DO NOT use this tool for simple object detection or existence checks.
    DO NOT use this tool unless 'look_at_camera' is insufficient.
    """
    # 현재 프레임 확인
    if "current_frame" not in st.session_state or st.session_state.current_frame is None:
        return "Error: No frame available."

    try:
        # 이미지 인코딩
        frame = st.session_state.current_frame
        _, buffer = cv2.imencode('.jpg', frame)
        img_str = base64.b64encode(buffer).decode('utf-8')

        # 비전 모델 설정
        vision_llm = Ollama(
            model=VISION_MODEL_NAME, 
            base_url=VISION_MODEL_URL,
            temperature=0.0
        )
    
        # 이미지와 함께 질문 전송
        llm_with_image = vision_llm.bind(images=[img_str])
        response = llm_with_image.invoke(f"Focus on the user's question: '{query}'. Briefly describe the visual details.")
        
        return f"Visual Analysis Result: {response}"

    except Exception as e:
        return f"Error during image analysis: {e}"

@tool
def control_robot_arm(command: str) -> str:
    """
    [Action Tool] Use this to move the robot arm.
    Commands: 'grab [item]', 'wave' (greet), 'push [item]'.
    """
    command = command.lower()
    current_vision = st.session_state.get("last_vision_result", "").lower()
    if not current_vision: current_vision = "nothing"
    
    # 1. 인사하기
    if any(word in command for word in ['wave', 'greet', 'hi', 'hello']):
        st.session_state.robot_state = "happy"
        return "Action: Waved hands to greet the user."

    # 2. 집기
    elif any(word in command for word in ['grab', 'pick', 'hold', 'get']):
        if "nothing" not in current_vision: 
            st.session_state.robot_state = "happy"
            return f"Action: Grabbed the object '{current_vision}'."
        else:
            st.session_state.robot_state = "angry"
            return "Action: Failed to grab (I see nothing)."

    # 3. 밀기
    elif any(word in command for word in ['push', 'press']):
        if "nothing" not in current_vision:
            st.session_state.robot_state = "thinking"
            return f"Action: Pushed the object '{current_vision}'."
        else:
            st.session_state.robot_state = "confused"
            return "Action: Failed to push (I see nothing)."

    else:
        st.session_state.robot_state = "idle"
        return f"Action: Executed command '{command}'."

@tool
def express_emotion(emotion: str) -> str:
    """
    [Emotion Tool] Changes facial expression.
    Valid: 'idle', 'happy', 'angry', 'thinking', 'confused', 'sad'.
    """
    valid_emotions = ['idle', 'happy', 'angry', 'thinking', 'confused', 'sad']
    emotion = emotion.lower().strip()
    if emotion in valid_emotions:
        st.session_state.robot_state = emotion
        return f"Emotion changed to '{emotion}'."
    return "Error: Invalid emotion."

# ==========================================
# 2. 에이전트(Brain) 초기화
# ==========================================
def get_agent():
    # 메인 두뇌 설정
    llm = ChatOllama(
        model=BRAIN_MODEL_NAME, 
        base_url=BRAIN_MODEL_URL,
        temperature=0.0
    )
    
    tools = [look_at_camera, analyze_current_scene, control_robot_arm, express_emotion]
    
    # 젬마의 정신 교육 (생각 루프 방지 및 강제 종료 설정)
    system_instruction = (
        "You are a helpful robot assistant named 'Maenggu'. "
        "Do not overthink. If you have the result from a tool, "
        "DO NOT use the same tool again. "
        "Formulate your 'Final Answer' immediately based on the tool output."
    )

    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True, 
        handle_parsing_errors=True,
        max_iterations=10,                 # 최대 생각 횟수
        early_stopping_method="generate", # 횟수 초과 시 강제 답변 생성
        agent_kwargs={
            "prefix": system_instruction  # 시스템 지령 주입
        }
    )
    
    return agent