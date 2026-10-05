# 판단과 agent 도구

`logic_brain.py`는 ChatOllama와 `initialize_agent`의 structured-chat executor를 만든다. session history는 ConversationBufferMemory, 종료 요청은 threading.Event로 관리한다. 모델 endpoint는 GlobalConfig에서 읽고 초기화 실패 시 로컬 llama3를 시도한다.

실제 ALL_TOOLS는 `vision_analyze`, `robot_action`, `grasp_object` 세 개다. `vision_detect.py`는 파일이 있지만 현재 목록 등록은 주석 처리되어 있다. 도구 응답과 agent callback은 `state_broadcaster`에 생각·intent를 알린다. 도구를 사용하지 않은 일부 완료 경로에서는 pipeline으로 intent를 전달한다.

`prompts.py`의 SYSTEM_INSTRUCTION이 있다는 것과 executor의 prefix로 활성화됐다는 것은 다르다. 현재 prefix 지정은 주석 처리돼 있다. `emotion_brain.py`는 robot/arm 상태를 읽어 감정 이벤트를 결정하고 `emotion_updater_deprecated.py`는 이전 코드다.

[LogicBrain](logic_brain.py) · [등록 도구](tools/__init__.py) · [현재 실행 흐름](../docs/ARCHITECTURE_STATUS.md)
