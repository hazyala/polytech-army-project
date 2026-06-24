import streamlit as st
from datetime import datetime
from langchain.tools import tool
from falkordb import FalkorDB
from logger import get_logger

logger = get_logger('TOOLS')

@tool
def memory_save(input_str: str) -> str:
    """
    사용자의 어명이 있을 때만 대화 내용을 FalkorDB 신경망에 영구 저장합니다.
    기본 저장 대상은 'Princess'입니다.
    """
    try:
        logger.info(f"memory_save 호출: {input_str}")
        
        # 1. 기본 사용자를 'Princess'로 설정 (마마의 권위를 최우선으로 함)
        current_user = st.session_state.get("current_user", "Princess")
        
        # 2. FalkorDB 연결 (마하세븐 브레인 함으로 접속)
        db = FalkorDB(host='localhost', port=6379)
        graph = db.select_graph('MachSeven_Memory')
        
        # 3. 데이터 저장 쿼리
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        save_query = """
        MATCH (u:User {name: $user_name})
        CREATE (u)-[:HAS_FACT]->(f:Fact {
            content: $content, 
            timestamp: $timestamp
        })
        RETURN f
        """
        
        params = {
            "user_name": current_user,
            "content": input_str.strip(),
            "timestamp": timestamp
        }
        graph.query(save_query, params)
        
        return f"✅ [{current_user}] 모드로 소중히 기억하였나이다: {input_str}"
        
    except Exception as e:
        logger.error(f"기억 저장 중 불충 발생: {e}")
        return f"❌ 송구하오나 기억 저장에 실패하였나이다: {str(e)}"