# Pybullet 환경 테스트 설명서  

## 업데이트 기록
### 2026.01.07  
- Web UI 가시성 개선
- 오브젝트 생성/제거 기능 추가
- 오브젝트 위치 제어 기능 추가
- 오브젝트 좌표 및 직선 거리 반환 기능 추가

### 2026.01.14
- 프로젝트 구조 개선
- Gripper 제어 기능 추가
- 오브젝트 종류(duck) 추가
- 오브젝트 고정 기능 추가
- Depth RAW 데이터 반환 기능 추가

### 2026.01.21
- 웹 소켓 통신 구현  
- 모델 Visual 수정  
- Gripper 가동 범위 수정 (0.08m -> 0.06m)  
- 엔드이펙터 위치 임시 조정 (-0.02m)  
- 축구공, 머그컵 오브젝트 추가  
- 오브젝트 고정 방식을 투명 발판 방식으로 변경  
- 로봇팔 및 오브젝트 마찰력 조정  

### 2026.02.03
- 엔드이펙터 시점 카메라 데이터 반환 기능 추가
- 그리퍼 상태(벌어진 정도) 반환 기능 추가
<br>  
<br>


## 웹 소켓 가이드
### 1. 웹 소켓 구현
`flask_server.py` 파일에 웹 소켓 통신을 구현하였습니다.  `SocketIO` 라이브러리를 사용하여 구현하였으며, 기존 HTTP 통신 방식처럼 URL을 사용하지 않고 **지속 연결 상태에서 이벤트를 통해 소통**합니다. 이를 통해 요청/응답 방식이 아닌, 서버에서 먼저 데이터를 보내는 것이 가능해졌습니다.  
### 2. 클라이언트에서의 웹 소켓 통신
클라이언트에서도 같은 라이브러리를 사용하는 것을 추천하며 본 가이드는 `SocketIO` 라이브러리를 기준으로 설명합니다. 다음은 Client -> Server 연결의 예제입니다.  
```
# Python에서 Client -> Flask 서버 연결의 간단한 예제

import socketio

sio = socketio.Client() # 소켓 객체 생성

@sio.event # 서버와 연결 시 실행됨
def connect():
	sio.emit('testevent', test_data) # 서버에 데이터를 송신하는 함수
    print("서버 연결됨")

@sio.on('message_from_server') # 서버로부터 데이터를 수신할 경우 실행됨
def on_message(data):
    print("서버로부터:", data)

@sio.event # 서버와 연결이 종료될 경우 실행됨
def disconnect():
    print("서버와 연결 종료")

sio.connect("http://localhost:5000") # 5000번 포트와 연결
sio.wait() # 프로그램이 종료되지 않도록 블로킹
```

### 3. 데이터 송수신 문법
- `@sio.on('이벤트이름')` : 상대방이 보낸 데이터를 수신하는 데코레이터입니다. 데코레이터 아래에 데이터 수신시 실행될 함수를 작성해야 합니다.
- `sio.emit('이벤트이름', 데이터)` : 상대에게 데이터를 보내는 함수입니다.  

데이터 송수신을 위해서는 서버와 클라이언트가 이벤트 이름을 맞춰야 하며, 본 문서에는 클라이언트가 Flask 서버와 통신하기 위한 이벤트 이름이 설명되어 있습니다.  
`flask_server.py` 파일의 코드를 참고할 수 있으나, 서버와 클라이언트의 코드에는 차이가 있으니 주의바랍니다.  
<br>  



## 1. 프로젝트 구조
📁 pybullet  
├── app.py # streamlit 실행 파일  
├── dofbot.urdf # 로봇 모델  
├── environment.yml # Anaconda 환경 파일   
├── flask_server.py # Flask 서버  
├── main.py    # 메인 실행 파일  
├── pybullet_sim.py # PyBullet 시뮬레이션   
├── README.md # You Are Here!   
└── shared_data.py # 공유 데이터  
<br>  


## 2.	Conda 환경 세팅
1. `pybullet.zip` 압축을 풉니다.  
2. Anaconda를 실행하여 프로젝트 폴더 경로로 이동합니다.  
3. 다음 명령어를 실행합니다. `conda env create -f environment.yml`  
4. 다음 명령어를 실행하여 Conda 환경을 실행합니다.`conda activate pybullet_env`  

*위 방식이 불가능한 경우 기존 환경에 아래 명령어로 필요한 라이브러리를 설치합니다.*  
`pip install flask-socketio python-socketio websocket-client`
<br>  
  

## 3.	PyBullet 실행 및 엔드포인트
1. `main.py`를 실행하여 PyBullet과 Flask 서버를 실행합니다.
2. **GET** (URL)
	- `“/”` : 실시간 비디오 스트림 (600*480)

	- `“/image”` : 이미지 (600*480)

	- `“/depth”` : Depth 이미지 RAW 데이터 (600*480) (m)  
  
	- `“/ee-video”` : 엔드이펙터 View 실시간 비디오 스트림 (600*480)  
  
	- `“/ee-image”` : 엔드이펙터 View 이미지 (600*480)  
  
	- `“/ee-depth”` : 엔드이펙터 View Depth 이미지 RAW 데이터 (600*480  (m)    
<br>  


## 4. 웹 소켓 이벤트 이름
### 4-1. server -> client
- `'robot_state'` : 로봇팔 정보  

	```
	# 데이터 형식  
	{  
		"ee": {"x": 0.1, "y": 0.0, "z": 0.47}, # 엔드이펙터 좌표 (m)
		"joints": [-45.0, 12.47, -57.93, -89.95, 0.0] # 각 조인트 각도 (deg)
		"gripper": 0.0 # 그리퍼 별려진 정도 : 0.0~0.06 (m)
	}  
	```  
<br>  

- `'object_state'` : 오브젝트 정보   

	```
	# 데이터 형식  
	{  
		"object": {  
			"exists": False, # 오브젝트 존재 여부
			"x": 0.0, "y": 0.0, "z": 0.0, # 오브젝트 현재 좌표 (m)
			"distance": 0.0 # 원점으로부터 오브젝트의 직선거리 (m) 
		}
	} 
	```  
<br>  

### 4-2. client -> server
- `'set_joints'` : 로봇팔 관절 각도 제어 (deg)

	```
	# 기대 형식
	{"joints": [deg1, deg2, deg3, deg4, deg5]}

	ex) {"joints": [0.0, 10.0, 15.0, 40.0, 20.0]}
	```  
	<br>

- `'set_gripper'` : 로봇팔 그리퍼 제어

	```
	# 기대 형식
	{"gripper": 0.0 ~ 0.06}

	ex) {"gripper": 0.05}
	```  
	<br>

- `'set_pos'` : 로봇팔 목표 좌표 설정

	```
	# 기대 형식
	{"pos": [x, y, z]}

	ex) {"pos": [0.1, 0.0, 0.3]}
	```  
	<br>

- `'set_force'` : 로봇팔 힘 설정 (기본값: 100)  

	```
	# 기대 형식
	{"force": int}

	ex) {"force": 100}
	```  
	<br>

- `'set_max_velocity'` : 로봇 동작 최대 속도 설정 (기본값 20)    

	```
	# 기대 형식
	{"max_velocity": float}

	ex) {"max_velocity": 5.0}
	```  
	<br>

- `'set_object'` : 오브젝트 생성/제거  

	```
	# 기대 형식
	{"op": "create", "object": "teddy", "fix": False}

	**파라미터**
		- op : create(생성) / delete(제거)
		- object : teddy(곰인형), duck(오리), soccerball(축구공)  
		- fix : True(고정) / False(비고정)
	```  
	<br>

- `'set_object_pos'` : 오브젝트 위치 제어  

	```
	# 기대 형식
	{"pos": [x, y, z]}
	
	ex) {"pos": [0.1, 0.0, 0.01]}
	```  
	<br>

## 5. Web UI
1. Anaconda에서 프로젝트 경로로 이동 후 다음 명령어를 실행합니다. `streamlit run app.py`
2. Web UI는 다음과 같이 구성되어 있습니다.  
<br>  

	|첫 번째 열|두 번쨰 열|세 번째 열|  
	|:--:|:--:|:--:|  
	|pybullet 내 카메라 화면|목표 좌표 입력 영역 (보내기 버튼 클릭 시 전송)|오브젝트 생성 버튼(고정, 타입 선택)|
	|Joint 제어 슬라이더|현재 End-Effector 좌표| 오브젝트 위치 제어 영역|
	|Gripper, 로봇 속도 제어 슬라이더||현재 오브젝트 좌표|

<br>

## [주의] 
- 서버에 오브젝트 변수를 하나만 선언했습니다. 따라서 오브젝트를 중첩해서 생성하면 이전 오브젝트를 제어할 수 없습니다. **오브젝트 생성 및 제어는 Web UI에서 하는 것을 추천합니다.**
- 오브젝트 고정에 사용되는 투명 발판은 오브젝트 생성시에는 바닥과 겹쳐지며 반투명하게 보입니다. 오브젝트를 공중으로 배치할 경우에는 투명하게 보입니다.
- 투명 발판은 오브젝트와의 접촉이 사라지면 잠시 뒤에 사라집니다.
- teddy 오브젝트 생성시 고정 옵션을 키면 곰인형이 뒤로 넘어집니다. 오브젝트 위치 이동시에는 넘어지지 않습니다.