import streamlit as st
import streamlit.components.v1 as components
import os
from logger import setup_terminal_logging
from engine import MachEngine
from face_renderer import render_face_svg 
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# 1. 시스템 기록 설정
setup_terminal_logging()

# 경로 설정
base_directory = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.join(base_directory, "..", "data")

# 2. 페이지 기본 설정
st.set_page_config(page_title="MACH VII - Control Center", layout="wide")

# CSS 스타일 정의 (기존 유지)
st.markdown("""
    <style>
    .main { overflow: hidden; height: 100vh; }
    [data-testid="stVerticalBlock"] > div:has(div.stImage) {
        background-color: #f0f2f6; border-radius: 15px; padding: 20px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.1);
    }
    .chat-container { height: calc(100vh - 200px); overflow-y: auto; padding-right: 10px; }
    
    .face-card {
        width: 100%; max-width: 400px; height: 400px;
        margin: 0 auto; background-color: #050505;
        border-radius: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        overflow: hidden; display: flex; justify-content: center; align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 세션 상태 초기화 (sim_mode 추가)
if "messages" not in st.session_state:
    st.session_state.update({
        "messages": [],
        "face_params": {"eye": 100, "mouth": 0, "color": "#FFFFFF"},
        "current_user": "Princess",
        "current_emotion": "IDLE",
        "sim_mode": False  # [추가] 파이불렛 시뮬레이션 모드 기본값
    })

# [수정] 엔진 로드 함수가 시뮬레이션 모드 여부를 인자로 받도록 변경
@st.cache_resource
def load_engine(sim_mode):
    # MachEngine이 초기화될 때 sim_mode를 전달하여 파이불렛 서버 사용 여부를 결정합니다.
    engine_instance = MachEngine(sim_mode=sim_mode)
    engine_instance.start_vision_loop()
    return engine_instance

# [추가] 사이드바 설정 영역
with st.sidebar:
    st.header("⚙️ SYSTEM CONTROL")
    st.divider()
    
    # 파이불렛 시뮬레이터 사용 여부를 결정하는 스위치입니다.
    # 스위치를 켜면 st.session_state.sim_mode가 True가 되며 엔진이 재시작됩니다.
    sim_switch = st.toggle("PyBullet Simulator Mode", value=st.session_state.sim_mode)
    
    # 스위치 상태가 바뀌었을 경우 세션 상태를 업데이트하고 화면을 갱신합니다.
    if sim_switch != st.session_state.sim_mode:
        st.session_state.sim_mode = sim_switch
        st.rerun()

    st.info(f"Active Mode: {'SIMULATION' if st.session_state.sim_mode else 'REAL WORLD'}")

# 현재 설정된 모드에 따라 엔진을 불러옵니다.
engine = load_engine(st.session_state.sim_mode)
st.session_state.engine = engine 

# 4. 화면 레이아웃 (기존 유지)
col_left, col_right = st.columns([1, 2.5])

# [좌측 패널]
with col_left:
    st.header("MACH VII")
    
    face_container = st.empty()
    st.session_state.face_container = face_container
    
    def draw_face():
        params = st.session_state.get("face_params", {"eye": 100, "mouth": 0, "color": "#FFFFFF"})
        raw_svg = render_face_svg(
            eye_openness=params.get("eye", 100),
            mouth_curve=params.get("mouth", 0),
            eye_color=params.get("color", "#FFFFFF")
        )
        clean_svg = " ".join(raw_svg.split())
        face_container.markdown(f'<div class="face-card">{clean_svg}</div>', unsafe_allow_html=True)

    draw_face()
    
    status_text = st.session_state.get("current_emotion", "IDLE").upper()
    st.subheader(f"Status: {status_text}")
    
    st.divider()
    st.markdown("### Vision Information")
    
    # [수정] 현재 모드에 따라 탐지 결과의 출처를 표시합니다.
    mode_tag = "[SIM]" if st.session_state.sim_mode else "[REAL]"
    st.info(f"{mode_tag} Detected: {engine.last_vision_result}")
    
    if engine.last_coordinates:
        with st.expander("Details", expanded=True):
            for coord in engine.last_coordinates:
                # 좌표 값을 cm 단위로 정렬하여 표시합니다.
                st.write(f"- {coord['name']}: X={coord['x']}, Y={coord['y']}, Z={coord['z']}cm")

# [우측 패널]
with col_right:
    chat_box = st.container(height=650)
    
    for msg in st.session_state.messages:
        with chat_box.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_input := st.chat_input("Input your command here..."):
        st.session_state.last_frame = engine.last_frame
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_box.chat_message("user"):
            st.write(user_input)
        
        with chat_box.chat_message("assistant"):
            st_callback = StreamlitCallbackHandler(st.container())
            # 에이전트 실행 시 현재 모드가 반영된 엔진을 사용합니다.
            answer = engine.run_agent(user_input, callbacks=[st_callback])
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()