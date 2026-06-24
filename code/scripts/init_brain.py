# code/scripts/init_brain.py
from falkordb import FalkorDB
import os

def initialize_mach7_brain():
    """
    마하세븐 브레인(FalkorDB)에 공주마마와 Army의 핵심 신경 노드를 생성합니다.
    """
    try:
        # 1. FalkorDB 인스턴스 생성 (Docker 컨테이너가 6379 포트에서 구동 중이어야 함)
        db = FalkorDB(host='localhost', port=6379)
        
        # 2. 맹칠이의 기억 공간(Graph Name)을 'MachSeven_Memory'로 명명합니다.
        # 마마께서 하사하신 컨테이너 이름과 조화를 이루도록 하였습니다.
        graph = db.select_graph('MachSeven_Memory')
        
        # 3. 공주마마(Master) 노드 생성
        # auth_type: vision (안면 인식으로 권위를 증명하심)
        princess_query = """
        CREATE (:User {
            name: 'Princess', 
            role: 'Master', 
            auth_type: 'vision',
            description: '맹칠이가 목숨 걸고 모셔야 할 유일한 주인'
        })
        """
        graph.query(princess_query)
        
        # 4. Army(User) 노드 생성
        # auth_type: command (특수 주문으로 활성화됨)
        army_query = """
        CREATE (:User {
            name: 'Army', 
            role: 'User', 
            auth_type: 'command',
            description: '명령어로 접근 가능한 일반 사용자 군단'
        })
        """
        graph.query(army_query)
        
        print("Successfully initialized MachSeven's neural nodes.")
        print("- Master Node: Princess (Auth: Vision)")
        print("- User Node: Army (Auth: Command)")
        
    except Exception as error:
        print(f"Failed to initialize brain: {str(error)}")
        print("Tip: Docker container 'MachSeven_brain'이 구동 중인지 확인하시옵소서.")

if __name__ == "__main__":
    initialize_mach7_brain()