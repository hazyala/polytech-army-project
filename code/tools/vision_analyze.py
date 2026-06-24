import streamlit as st
import base64
import requests
import cv2
from langchain_core.tools import tool
from logger import get_logger

logger = get_logger('TOOLS')

@tool
def vision_analyze(query: str) -> str:
    """현재 카메라의 스냅샷 이미지를 LLM에게 직접 전달하여 상세 분석합니다."""
    try:
        # [수정 핵심] 세션에 저장된 엔진에서 최신 프레임을 직접 가져옵니다.
        if "engine" not in st.session_state:
            return "엔진이 준비되지 않았습니다."
            
        frame = st.session_state.engine.last_frame
        if frame is None: return "영상을 찾을 수 없습니다."
        
        # 이미지 최적화 및 Base64 인코딩
        resized = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 분석 서버(Gemma3 27b)에 이미지와 질문 전송
        response = requests.post(
            "http://ollama.aikopo.net/api/generate",
            json={
                "model": "gemma3:27b",
                "prompt": query,
                "images": [image_base64],
                "stream": False
            },
            timeout=180
        )
        
        if response.status_code == 200:
            return response.json().get('response', '분석 결과가 없습니다.')
        return f"분석 서버 오류 (코드: {response.status_code})"
    except Exception as e:
        logger.error(f"vision_analyze 오류: {e}")
        return f"분석 중 오류 발생: {str(e)}"