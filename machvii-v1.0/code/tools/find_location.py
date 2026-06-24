import streamlit as st
from langchain_core.tools import tool
from logger import get_logger

logger = get_logger('TOOLS')

@tool
def find_location(target: str) -> str:
    """
    마지막으로 감지된 객체의 좌표 검색
    
    Args:
        target: 찾을 객체명 (예: "cup", "person", "bottle")
    
    Returns:
        객체의 좌표 (x, y, z) 또는 "찾을 수 없음"
    """
    try:
        logger.info(f"find_location 호출: {target}")
        
        if "last_coordinates" not in st.session_state:
            logger.warning("좌표 정보 없음")
            return f"{target}을(를) 찾을 수 없습니다."
        
        coordinates = st.session_state.last_coordinates
        
        if not coordinates:
            return f"{target}을(를) 찾을 수 없습니다."
        
        target_lower = target.lower()
        
        for coord in coordinates:
            if coord['name'].lower() == target_lower:
                # 단위를 mm에서 cm로 변경하여 위치 정보를 반환합니다.
                result = (
                    f"{target}의 위치: "
                    f"X={coord['x']}, Y={coord['y']}, Z={coord['z']}cm"
                )
                logger.info(result)
                return result
        
        logger.info(f"{target}을(를) 찾을 수 없음")
        return f"{target}을(를) 찾을 수 없습니다."
        
    except Exception as e:
        logger.error(f"find_location 오류: {e}")
        return f"오류 발생: {str(e)}"