import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import av
import threading
import numpy as np
from PIL import Image
import hashlib
import time
import os # 경로 계산을 위해 추가
# vision.py에서 VisionSystem 클래스를 가져옵니다.
from vision import VisionSystem 
from agent import get_agent

# 페이지 설정
st.set_page_config(layout="wide", page_title="Army 2D Simulator")

# === [0] 이미지 경로 설정 (여기가 핵심!) ===
# main.py 파일이 있는 위치를 기준으로 assets 폴더를 찾습니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "assets", "images")

def get_emotion_image_path(emotion):
    """감정에 맞는 이미지의 절대 경로를 반환합니다."""
    return os.path.join(IMAGE_DIR, f"{emotion}.gif")

# === [1] 상태 및 초기화 ===

if "vision_system" not in st.session_state:
    try:
        # VisionSystem 클래스 초기화 (안전장치)
        st.session_state.vision_system = VisionSystem('yolov8n.pt')
    except Exception as e:
        st.error(f"비전 시스템 초기화 실패: {e}")

if "agent" not in st.session_state:
    st.session_state.agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 젬마의 기억 (텍스트)
if "last_vision_result" not in st.session_state:
    st.session_state.last_vision_result = "Nothing detected."

# 젬마의 눈 (이미지 프레임)
if "current_frame" not in st.session_state:
    st.session_state.current_frame = None

# 도배 방지용 변수들
if "last_reacted_objects" not in st.session_state:
    st.session_state.last_reacted_objects = ""

if "last_photo_hash" not in st.session_state:
    st.session_state.last_photo_hash = ""

if "robot_state" not in st.session_state:
    st.session_state.robot_state = "idle"

lock = threading.Lock()


# === [2] 상황 판단 및 반응 함수 (족쇄 채움!) ===
def check_and_react(text_result, is_manual=False):
    """
    상황을 판단하고 젬마(Agent)를 호출합니다.
    """
    # 1. CCTV 모드일 때 중복/빈값 필터링
    if not is_manual:
        if not text_result or "nothing" in text_result.lower():
            return
        if text_result == st.session_state.last_reacted_objects:
            return
    
    # 2. 반응 기록 갱신
    st.session_state.last_reacted_objects = text_result
    
    # 3. 프롬프트 구성 (★여기가 핵심이옵니다!★)
    # 젬마에게 "자동 알림일 때는 절대 그림 보지 마라"고 신신당부합니다.
    
    base_instruction = (
        f"Detected Objects (YOLO): '{text_result}'.\n"
        "Your task: React to these objects briefly in Korean."
    )

    if is_manual:
        # [수정] 수동으로 찍었을 때도, 일단은 텍스트로만 대답하게 유도
        # (사용자가 '자세히 봐줘'라고 안 했으므로)
        prompt = (
            f"{base_instruction}\n"
            "NOTE: Do NOT use 'analyze_current_scene' yet. Just trust the YOLO text labels.\n"
            "Only greet or suggest help based on the object names."
        )
    else:
        # [수정] CCTV 자동 모드: 그림 보기 절대 금지!
        prompt = (
            f"{base_instruction}\n"
            "CRITICAL: Do NOT use the 'analyze_current_scene' tool.\n"
            "CRITICAL: Do NOT describe visual details like colors or clothes.\n"
            "Just say something like '사람이 보이네요' or '펜이 있군요'. Keep it simple."
        )
    
    # 4. 젬마 호출
    try:
        # 스피너 표시
        if is_manual:
            with st.spinner("맹구가 텍스트 정보를 확인 중이옵니다..."):
                response = st.session_state.agent.run(prompt)
        else:
            # 자동일 때는 조용히 처리
            response = st.session_state.agent.run(prompt)
        
        # 'PASS'가 아니면 반응 출력
        if not is_manual and "PASS" in response:
            return

        st.session_state.robot_state = "happy"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.toast(f"🤖 맹구: {response}", icon="💬")
        
        # 화면 갱신
        st.rerun()
            
    except Exception as e:
        if is_manual:
            st.error(f"판단 중 오류: {e}")
        else:
            print(f"Auto-check error: {e}")


# === [3] WebRTC 처리기 ===
class VideoProcessor(VideoTransformerBase):
    def __init__(self):
        # 세션 상태에서 안전하게 vision_system 가져오기
        if "vision_system" in st.session_state:
            self.vision = st.session_state.vision_system
        else:
            self.vision = None
            
        self.latest_text = ""
        self.latest_frame = None

    def recv(self, frame):
        try:
            if self.vision is None: return frame
            
            # 이미지 변환 (av -> numpy)
            img = frame.to_ndarray(format="bgr24")
            
            # YOLO 분석 수행
            processed_img, text = self.vision.process_frame(img)
            
            # 결과 저장 (메인 스레드 공유용)
            with lock:
                self.latest_text = text
                self.latest_frame = img # 원본 이미지 저장
            
            # 박스 그려진 이미지 반환
            return av.VideoFrame.from_ndarray(processed_img, format="bgr24")
        except:
            return frame


# === [4] 메인 UI ===
st.title("🛡️ Army 2D Simulator (Fixed Images)")

col1, col2 = st.columns([2, 1])

# --- 왼쪽: 카메라 ---
with col1:
    st.subheader("🎥 Vision Input")
    tab1, tab2 = st.tabs(["📸 수동 촬영", "📹 자율 CCTV"])
    
    # [Tab 1] 수동 모드
    with tab1:
        st.caption("버튼을 누르면 사진을 찍고 분석합니다.")
        img_file = st.camera_input("찰칵! (정밀 분석)")
        
        if img_file is not None:
            # 이미지 중복 방지용 해시 생성
            bytes_data = img_file.getvalue()
            current_hash = hashlib.md5(bytes_data).hexdigest()
            
            # 새로운 사진일 때만 실행
            if current_hash != st.session_state.last_photo_hash:
                st.session_state.last_photo_hash = current_hash
                
                image = Image.open(img_file)
                frame = np.array(image)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                if "vision_system" in st.session_state:
                    vision = st.session_state.vision_system
                    processed_frame, text_result = vision.process_frame(frame)
                    
                    # 젬마 기억 & 눈 업데이트
                    st.session_state.last_vision_result = text_result
                    st.session_state.current_frame = frame 
                    
                    st.image(processed_frame, caption=f"탐지됨: {text_result}", channels="BGR")
                    
                    # 강제 반응 호출 (수동 모드)
                    check_and_react(text_result, is_manual=True)
                else:
                    st.error("시스템 오류: 비전 시스템 없음")
            else:
                st.info("이미 확인한 사진이옵니다.")

    # [Tab 2] 자율 CCTV 모드
    with tab2:
        st.caption("카메라가 켜져 있으면 맹구가 계속 지켜봅니다.")
        ctx = webrtc_streamer(
            key="cctv-auto",
            video_processor_factory=VideoProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            async_processing=True,
        )
        
        # CCTV 정보 실시간 표시 공간
        cctv_status = st.empty()
        
        # CCTV가 작동 중일 때 데이터 가져오기
        if ctx.state.playing and ctx.video_processor:
            with lock:
                current_text = ctx.video_processor.latest_text
                current_frame = ctx.video_processor.latest_frame
            
            # 정보 갱신
            if current_text:
                st.session_state.last_vision_result = current_text
                if current_frame is not None:
                    st.session_state.current_frame = current_frame
                
                cctv_status.info(f"👀 실시간 시야: {current_text}")
                
                # 자율 반응 시도 (자동 모드)
                check_and_react(current_text, is_manual=False)

# --- 오른쪽: 맹구 & 채팅 ---
with col2:
    st.subheader("🤖 맹구 (Maenggu)")
    
    # [수정됨] 감정 이미지 표시 로직 (절대 경로 사용)
    emotion = st.session_state.robot_state
    img_path = get_emotion_image_path(emotion) # 경로 계산 함수 사용
    
    if os.path.exists(img_path):
        st.image(img_path, caption=f"상태: {emotion.upper()}", use_container_width=True)
    else:
        # 이미지가 없을 경우 텍스트로 대체하고 경로 힌트 출력 (디버깅용)
        st.warning(f"이미지를 찾을 수 없사옵니다: {emotion}")
        st.caption(f"찾아본 경로: {img_path}")
    
    st.divider()
    
    chat_container = st.container(height=400)
    for msg in st.session_state.messages:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("명령하기..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
            
        with chat_container.chat_message("assistant"):
            with st.spinner("생각 중..."):
                full_response = st.session_state.agent.run(prompt)
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

# === [핵심] 자율 감시 루프 ===
# CCTV가 켜져 있다면, 1.5초 뒤에 스스로 화면을 갱신해서 계속 감시하게 만듭니다.
if ctx.state.playing:
    time.sleep(1.5)
    st.rerun()