import streamlit as st
from langchain_core.tools import tool
from logger import get_logger

logger = get_logger('TOOLS')

@tool
def vision_detect(query: str) -> str:
    """실시간 카메라에서 감지된 물체와 좌표를 엔진에서 가져옵니다."""
    try:
        if "engine" not in st.session_state: 
            return "엔진이 준비되지 않았습니다."
        
        engine = st.session_state.engine
        
        result_text = engine.last_vision_result
        coords = engine.last_coordinates
        
        if coords:
            # 단위를 mm에서 cm로 변경하여 보고 문구를 생성합니다.
            res = f"감지 결과: {result_text}\n"
            for c in coords:
                res += f"- {c['name']}: (x={c['x']}, y={c['y']}, z={c['z']}cm)\n"
            return res
            
        return f"감지 결과: {result_text}"
    except Exception as e:
        logger.error(f"탐지 도구 오류: {e}")
        return "정보 획득 실패"