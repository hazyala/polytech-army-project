import streamlit as st
from langchain_core.tools import tool
from falkordb import FalkorDB
from logger import get_logger

# 도구 로그 기록을 위한 로거 설정
logger = get_logger('TOOLS')

@tool
def memory_load(query: str) -> str:
    """
    현재 접속 중인 사용자의 기억 신경망(FalkorDB)에서 정보를 조회합니다.
    기본적으로 'Princess' 혹은 'Army' 노드와 연결된 사실(Fact)을 찾습니다.
    """
    try:
        logger.info(f"memory_load 호출: {query}")
        
        # 1. 세션 상태에서 현재 사용자를 확인 (기본은 Princess)
        current_user = st.session_state.get("current_user", "Princess")
        
        # 2. FalkorDB 연결 및 그래프 선택
        db = FalkorDB(host='localhost', port=6379)
        graph = db.select_graph('MachSeven_Memory')
        
        # 3. 기억 검색 쿼리 (현재 사용자와 연결된 Fact 노드만 조회)
        search_query = """
        MATCH (u:User {name: $user_name})-[:HAS_FACT]->(f:Fact)
        WHERE f.content CONTAINS $search_text
        RETURN f.content, f.timestamp
        ORDER BY f.timestamp DESC
        """
        
        params = {
            "user_name": current_user,
            "search_text": query
        }
        
        result = graph.query(search_query, params)
        
        # 4. 결과가 없을 경우 처리
        if not result.result_set:
            return f"[{current_user}]님에 대한 '{query}' 관련 기억을 찾을 수 없습니다."
            
        # 5. 결과 목록 생성
        memories = [f"- {row[0]} (기록: {row[1]})" for row in result.result_set]
        
        response = f"✅ [{current_user}]님의 기억 창고에서 다음 내용을 찾았습니다:\n" + "\n".join(memories)
        logger.info(f"조회 성공: {len(memories)}건")
        return response
        
    except Exception as e:
        logger.error(f"memory_load 오류: {e}")
        return f"❌ 기억 조회 중 오류가 발생했습니다: {str(e)}"