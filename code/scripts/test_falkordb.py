# test_falkordb.py
from falkordb import FalkorDB

def verify_falkordb_connection():
    """
    FalkorDB 서버와의 연결을 확인하고 기본적인 그래프 명령을 수행합니다.
    """
    try:
        # 1. FalkorDB 인스턴스 생성 (Docker로 실행 중인 6379 포트 연결)
        # host는 로컬 환경이므로 'localhost'를 사용합니다.
        db = FalkorDB(host='localhost', port=6379)
        
        # 2. 'test_memory'라는 이름의 그래프 공간을 선택합니다.
        graph = db.select_graph('test_memory')
        
        # 3. 테스트 노드를 생성합니다. (공주마마 노드 생성)
        # Cypher 쿼리문을 사용하여 그래프 구조로 데이터를 저장합니다.
        graph.query("CREATE (:User {name: 'Princess', rank: 'Master'})")
        
        # 4. 저장된 데이터를 다시 불러와 연결을 최종 확인합니다.
        result = graph.query("MATCH (u:User) RETURN u.name")
        
        # 결과 출력: 성공 시 [['Princess']] 형태의 데이터가 보여야 합니다.
        print(f"FalkorDB 연결 성공! 조회 결과: {result.result_set}")
        
        # 5. 테스트 완료 후 임시 그래프를 삭제하여 정리합니다.
        graph.delete()
        print("테스트용 그래프가 성공적으로 삭제되었습니다.")
        
    except Exception as e:
        # 연결 실패 시 오류 원인을 출력합니다. (예: Docker 미구동 등)
        print(f"FalkorDB 연결 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    verify_falkordb_connection()