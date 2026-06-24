import streamlit as st
import streamlit.components.v1 as components

def render_face_svg(eye_openness=100, mouth_curve=0, eye_color="#00FFFF", glow_intensity=0.6):
    """
    EMO 스타일의 얼굴을 그리는 SVG 생성기
    눈 깜빡임 애니메이션 및 입 위치/곡률 최적화 버전
    """
    
    # 캔버스 크기 설정
    canvas_width = 400
    canvas_height = 400 
    
    # 1. 눈의 기하학적 계산
    base_eye_width = 100
    base_eye_height = 110
    
    # 눈 위치 (Y축): 화면 상단 쪽에 배치하여 귀여운 비율 유지
    center_y_axis = 160 
    
    current_eye_height = base_eye_height * (eye_openness / 100.0)
    eye_y_pos = center_y_axis - (current_eye_height / 2)
    corner_radius = 20 if eye_openness > 20 else 5

    # 2. 입의 기하학적 계산
    # 입 높이를 230으로 설정하여 눈과 가깝게 배치
    mouth_base_y = 250 
    mouth_start_x, mouth_start_y = 160, mouth_base_y
    mouth_end_x, mouth_end_y = 240, mouth_base_y
    
    # 제어점 계산: 계수를 1.5로 조정하여 자연스러운 미소 구현
    control_y = mouth_base_y + (mouth_curve * 1.5) 
    
    # 입의 가시성 (값이 작을 경우 무표정 처리)
    mouth_opacity = 0 if abs(mouth_curve) < 5 else 1.0

    # 3. SVG 코드 조립
    svg_html = f"""
    <svg width="100%" height="100%" viewBox="0 0 {canvas_width} {canvas_height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="{canvas_width}" height="{canvas_height}" fill="#050505" rx="40" ry="40"/>
        
        <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                <feComponentTransfer in="coloredBlur" result="glow_adjusted">
                    <feFuncA type="linear" slope="{glow_intensity + 0.5}"/>
                </feComponentTransfer>
                <feMerge>
                    <feMergeNode in="glow_adjusted"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>

            <style>
                /* 눈 깜빡임 애니메이션 */
                @keyframes blink {{
                    0%, 90%, 100% {{ transform: scaleY(1); }}
                    95% {{ transform: scaleY(0.1); }}
                }}

                /* 눈 스타일: 반응 속도를 0.2초로 단축하여 실시간 느낌 강조 */
                .face-part {{
                    transition: all 0.2s ease-out;
                    transform-box: fill-box;
                    transform-origin: center;
                    animation: blink 3s infinite;
                }}
                
                /* 입 스타일: d(경로) 변화 시 부드럽게 이어지도록 설정 */
                .mouth-part {{
                    transition: d 0.2s ease-out, opacity 0.2s ease;
                }}
            </style>
        </defs>

        <g filter="url(#glow)" fill="{eye_color}" stroke="{eye_color}">
            <rect class="face-part" x="60" y="{eye_y_pos}" width="{base_eye_width}" height="{current_eye_height}" 
                  rx="{corner_radius}" ry="{corner_radius}" stroke="none" />
            
            <rect class="face-part" x="240" y="{eye_y_pos}" width="{base_eye_width}" height="{current_eye_height}" 
                  rx="{corner_radius}" ry="{corner_radius}" stroke="none" />
            
            <path class="mouth-part" d="M {mouth_start_x} {mouth_start_y} Q 200 {control_y} {mouth_end_x} {mouth_end_y}"
                  stroke-width="8" fill="transparent" stroke-linecap="round"
                  opacity="{mouth_opacity}" />
        </g>
    </svg>
    """
    return svg_html

@st.fragment
def face_controller_fragment():
    """
    슬라이더와 얼굴 출력부만 독립적으로 빠르게 실행하는 프래그먼트 함수
    """
    col_ctrl, col_view = st.columns([1, 1.5])
    
    with col_ctrl:
        st.subheader("🎛️ 파라미터 조절")
        eye_open = st.slider("눈 크기", 0, 100, 100)
        # 마마께서 명하신 -80 ~ 40 범위 유지
        mouth_val = st.slider("입꼬리 (감정)", -60, 40, 0) 
        color_val = st.color_picker("색상", "#00FFFF")
        glow_val = st.slider("광원 세기", 0.0, 1.0, 0.7)

    with col_view:
        st.subheader("📺 실시간 미리보기")
        face_svg = render_face_svg(eye_open, mouth_val, color_val, glow_val)
        
        container_style = """
        <div style="
            border: 4px solid #333; 
            border-radius: 20px; 
            padding: 10px; 
            background-color: #000;
            display: flex; justify-content: center;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);">
        """
        st.markdown(container_style, unsafe_allow_html=True)
        # height를 넉넉하게 설정하여 잘림 방지
        components.html(face_svg, height=420, scrolling=False)
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="EMO Face Generator", layout="centered")
    st.title("🤖 맹칠이 표정 연구소 v2.2")
    st.divider()
    
    # 프래그먼트 함수 호출 (이 구역만 부분적으로 고속 새로고침됨)
    face_controller_fragment()

if __name__ == "__main__":
    main()