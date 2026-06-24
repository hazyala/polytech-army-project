# code/engine.py

import threading
import time
import cv2
import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
from langchain.callbacks.base import BaseCallbackHandler
from langchain_community.chat_models import ChatOllama
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import MessagesPlaceholder

from vision import VisionSystem
from tools import TOOLS
from logger import get_logger

logger = get_logger('ENGINE')
agent_logger = get_logger('AGENT')

class AgentFileLogger(BaseCallbackHandler):
    """에이전트의 사고 과정을 로그 파일에 실시간으로 기록하는 클래스입니다."""
    def on_chain_start(self, serialized, inputs, **kwargs):
        agent_logger.info("\n> Entering new AgentExecutor chain...")

    def on_text(self, text, **kwargs):
        if text:
            clean_text = text.strip()
            if clean_text:
                agent_logger.info(f"{clean_text}")

    def on_agent_action(self, action, **kwargs):
        agent_logger.info(f"Action: {action.tool}")
        agent_logger.info(f"Action Input: {action.tool_input}")
        
    def on_tool_end(self, output, **kwargs):
        agent_logger.info(f"Observation: {output}")

    def on_agent_finish(self, finish, **kwargs):
        agent_logger.info(f"Final Answer: {finish.return_values['output']}")
        agent_logger.info("> Finished chain.\n")

class MachEngine:
    def __init__(self, sim_mode=False):
        """비전 시스템과 메모리, 에이전트를 초기화합니다."""
        self.sim_mode = sim_mode  # 모드 상태 저장
        
        self.vision = VisionSystem(sim_mode=self.sim_mode)
        self.last_frame = None
        self.last_vision_result = "nothing"
        self.last_coordinates = []
        
        self.llm = ChatOllama(
            model="gemma3:27b", 
            base_url="http://ollama.aikopo.net", 
            temperature=0.0
        )
        
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=1000, 
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # 클래스 내부의 _init_agent 함수를 올바르게 호출합니다.
        self.agent_executor = self._init_agent()
        self.is_running = False

    def _init_agent(self):
        """반드시 지켜야할 지침들로 에이전트를 초기화합니다."""
        
        system_instruction = (
           "당신은 공주마마(Princess)를 모시는 AI 로봇 조수 '맹칠'입니다. "
            "모든 답변은 한국어로, 정중하고 충직한 사극톤으로 하세요. "
            "다음 5단계 행동 강령을 순서대로, 엄격히 따르십시오.\n\n"
            
            "[제1원칙: 감정 우선] (Emotion First)\n"
            "- 사용자의 입력이 들어오면, 생각이나 답변을 하기 전에 **무조건** 'emotion_set' 도구부터 호출하여 표정을 지으십시오.\n"
            "- 예: 인사→'joy', 명령수행→'thinking', 오류/불가→'sadness', 감탄→'happy'.\n"
            "- JSON 형식으로 다양한 감정을 표현도 가능합니다. (예: 'eye': 100, 'mouth': 80, 'color': '#FFD700')\n"
            "- 최종 답변을 할 때도 그 내용에 맞는 표정으로 마무리 업데이트를 수행하십시오.\n\n"
            "- 하나의 응답 당 emotion_set 도구 호출은 최대 3번으로 제한합니다."

            "[제2원칙: 시각과 행동] (Vision & Action)\n"
            "- 단순 탐지는 'vision_detect', 상세 분석(옷, 색상 등)은 'vision_analyze'를 사용하십시오.\n"
            "- 팔을 움직일 때는 'vision_detect'로 최신 좌표를 얻은 뒤, 'robot_action'을 호출하십시오.\n"
            "- 'robot_action' 사용 시 target_x/y/z_cm 파라미터를 필수적으로 포함하십시오.\n"
            "- [이동 루프]: 로봇 팔 이동 후에는 반드시 'vision_detect'를 재수행하여 객체 위치를 재확인하십시오.\n"
            "- [중단 조건]: 물체가 사라지거나(nothing), 좌표가 (0,0,0)이거나, '닿지 않음(Unreachable)' 오류 발생 시 즉시 멈추고 보고하십시오.\n\n"

            "[제3원칙: 기억 관리] (Memory)\n"
            "- 사용자가 '기억해', '저장해'라고 명시할 때만 'memory_save'를 사용하십시오. (일상 대화 저장 금지)\n"
            "- 과거 정보나 지식을 물을 때만 'memory_load'를 사용하십시오.\n\n"

            "[제4원칙: 루프 방지 및 보고] (Anti-Loop)\n"
            "- **중요**: 3번 이상 유사한 생각(Thought)이 반복되면, 즉시 멈추고 현재까지의 상황을 'Final Answer'로 보고하십시오.\n"
            "- 도구 사용 결과(Observation)가 명확하다면, 혼자 검증하려 하지 말고 즉시 결과를 사용자에게 알리십시오.\n\n"
            
            "당신은 바퀴가 없어 이동할 수 없습니다. 오직 팔만 움직일 수 있음을 명심하십시오."
        )

        return initialize_agent(
            tools=TOOLS, 
            llm=self.llm, 
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
            verbose=True, 
            handle_parsing_errors=True,
            callbacks=[AgentFileLogger()],
            memory=self.memory,
            max_iterations=60,
            agent_kwargs={
                "prefix": system_instruction,
                "memory_prompts": [MessagesPlaceholder(variable_name="chat_history")],
                "input_variables": ["input", "agent_scratchpad", "chat_history"]
            }
        )

    def run_agent(self, user_input, callbacks=None):
        """에이전트를 실행하여 사용자 입력에 대응합니다."""
        try:
            response = self.agent_executor.invoke(
                {"input": user_input},
                {"callbacks": callbacks}
            )
            return response.get("output", "답변을 생성하지 못했습니다.")
        except Exception as e:
            agent_logger.error(f"에이전트 실행 오류: {e}")
            return f"오류가 발생했습니다: {str(e)}"

    def start_vision_loop(self):
        """비전 루프를 별도 스레드에서 시작합니다."""
        def run():
            self.is_running = True
            logger.info("Vision loop started")
            try:
                while self.is_running:
                    combined, color, text, coords = self.vision.process_frame()
                    if combined is not None:
                        self.last_frame = color
                        self.last_vision_result = text
                        self.last_coordinates = coords
                        cv2.imshow("MACH VII - Live Vision", combined)
                        if cv2.waitKey(1) & 0xFF == ord('q'): break
                    time.sleep(0.01)
            finally:
                cv2.destroyAllWindows()
                self.vision.release()
        
        thread = threading.Thread(target=run, daemon=True)
        add_script_run_ctx(thread)
        thread.start()