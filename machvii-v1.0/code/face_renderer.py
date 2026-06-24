# code/face_renderer.py

def render_face_svg(eye_openness=100, mouth_curve=0, eye_color="#FFFFFF", glow_intensity=0.7):
    """
    맹칠이의 얼굴을 그리는 모듈
    [기능 추가] 3초마다 인간처럼 눈을 깜빡이는 CSS 애니메이션 탑재
    """
    canvas_width, canvas_height = 400, 400
    
    # 1. 눈 좌표 계산 (Python이 계산한 '현재 눈 크기')
    base_eye_w, base_eye_h = 100, 110
    center_y = 160 
    curr_eye_h = base_eye_h * (eye_openness / 100.0)
    eye_y = center_y - (curr_eye_h / 2)
    radius = 20 if eye_openness > 20 else 5

    # 2. 입 좌표 계산
    mouth_base_y = 240
    mouth_sx, mouth_sy = 160, mouth_base_y
    mouth_ex, mouth_ey = 240, mouth_base_y
    control_y = mouth_base_y + (mouth_curve * 1.5)
    mouth_opacity = 0 if abs(mouth_curve) < 5 else 1.0

    # 3. SVG 생성 (CSS Animation 적용)
    svg_code = f"""
    <svg width="100%" height="100%" viewBox="0 0 {canvas_width} {canvas_height}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                <feComponentTransfer in="coloredBlur" result="glow_adjusted">
                    <feFuncA type="linear" slope="{glow_intensity + 0.5}"/>
                </feComponentTransfer>
                <feMerge><feMergeNode in="glow_adjusted"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            
            <style>
                /* 눈 깜빡임 애니메이션 정의 */
                @keyframes blink {{
                    0%, 90%, 100% {{ transform: scaleY(1); }} /* 0~2.7초: 원래 크기 유지 */
                    95% {{ transform: scaleY(0.1); }}         /* 2.85초: 눈 감음 (10% 크기) */
                }}

                /* 눈 (Eyes) 스타일 */
                .face-part {{
                    /* 1. 감정 변화 시 부드러운 전환 (기존 기능 유지) */
                    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    
                    /* 2. 애니메이션 적용을 위한 기준점 설정 (중앙 기준 수축) */
                    transform-box: fill-box;
                    transform-origin: center;
                    
                    /* 3. 3초마다 무한 깜빡임 실행 */
                    animation: blink 3s infinite;
                }}
                
                /* 입 (Mouth) 스타일 - 입은 깜빡이면 안 됨 */
                .mouth-part {{
                    transition: d 0.5s ease-out, opacity 0.3s ease, stroke 0.5s ease;
                }}
            </style>
        </defs>
        
        <rect width="{canvas_width}" height="{canvas_height}" fill="#050505" rx="40" ry="40"/>
        
        <g filter="url(#glow)" fill="{eye_color}" stroke="{eye_color}">
            <rect class="face-part" x="60" y="{eye_y}" width="{base_eye_w}" height="{curr_eye_h}" rx="{radius}" ry="{radius}" stroke="none" />
            <rect class="face-part" x="240" y="{eye_y}" width="{base_eye_w}" height="{curr_eye_h}" rx="{radius}" ry="{radius}" stroke="none" />
            
            <path class="mouth-part" d="M {mouth_sx} {mouth_sy} Q 200 {control_y} {mouth_ex} {mouth_ey}"
                  stroke-width="8" fill="transparent" stroke-linecap="round" opacity="{mouth_opacity}" />
        </g>
    </svg>
    """
    return svg_code