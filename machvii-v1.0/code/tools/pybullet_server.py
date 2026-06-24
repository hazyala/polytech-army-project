import requests
import numpy as np
import cv2

class PyBulletServer:
    """
    본진(MACH_SEVEN)에서 연무장 서버(Flask)와 통신을 담당하는 전령 클래스입니다.
    데이터 수신 및 로봇 제어 명령 전달을 전담합니다.
    """
    def __init__(self, ip="127.0.0.1", port=5000):
        # 서버 접속을 위한 기본 주소를 설정합니다.
        self.base_url = f"http://{ip}:{port}"

    def get_rgb_image(self):
        """
        연무장 서버로부터 실시간 카메라 화면(RGB)을 가져옵니다.
        YOLO 탐지에서 사용할 수 있도록 OpenCV 이미지 형식으로 변환합니다.
        """
        try:
            # 서버의 /image 엔드포인트에 그림 데이터를 요청합니다.
            r = requests.get(f"{self.base_url}/image", timeout=1)
            if r.status_code == 200:
                # 받은 바이트 데이터를 숫자 배열(numpy)로 바꾼 뒤 이미지로 복원합니다.
                img_array = np.frombuffer(r.content, np.uint8)
                return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"이미지 수신 실패: {e}")
        return None

    def get_depth_data(self):
        """
        연무장 서버로부터 깊이 정보(Depth Map)를 가져옵니다.
        물체와의 거리를 계산하기 위해 숫자 배열 형태로 반환합니다.
        """
        try:
            # 서버의 /depth 엔드포인트에 깊이 데이터를 요청합니다.
            r = requests.get(f"{self.base_url}/depth", timeout=1)
            if r.status_code == 200:
                # JSON 형태의 데이터를 받아 실수형(float32) 숫자 배열로 변환합니다.
                return np.array(r.json(), dtype=np.float32)
        except Exception as e:
            print(f"깊이 데이터 수신 실패: {e}")
        return None

    def move_arm(self, position):
        """
        로봇팔 끝단(End-Effector)을 목표 좌표 [x, y, z]로 이동시킵니다.
        단위는 미터(m)를 사용합니다.
        """
        try:
            # 목표 좌표를 JSON 형식으로 담아 서버에 전송합니다.
            r = requests.post(f"{self.base_url}/set_pos", json={"pos": position}, timeout=1)
            return r.json().get("ok", False)
        except Exception as e:
            print(f"이동 명령 실패: {e}")
            return False

    def get_arm_position(self):
        """
        현재 로봇팔 끝단의 실제 좌표(x, y, z)를 서버로부터 가져옵니다.
        """
        try:
            r = requests.get(f"{self.base_url}/ee", timeout=1)
            return r.json()
        except Exception as e:
            print(f"좌표 확인 실패: {e}")
        return None

    def control_object(self, name, op="create"):
        """
        연무장에 물체를 새로 생성(create)하거나 제거(delete)합니다.
        """
        try:
            body = {"object": name, "op": op}
            r = requests.post(f"{self.base_url}/set_object", json=body, timeout=1)
            return r.json().get("ok", False)
        except Exception as e:
            print(f"물체 제어 실패: {e}")
            return False