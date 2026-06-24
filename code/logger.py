import logging
import sys
import os
from datetime import datetime

class TerminalTee:
    """
    터미널 출력 내용을 가로채서 파일에도 동시에 기록하는 클래스입니다.
    """
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")

    def write(self, message):
        """터미널과 로그 파일 양쪽에 메시지를 작성합니다."""
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        """출력 버퍼를 비워 기록을 확정합니다."""
        self.terminal.flush()
        self.log_file.flush()

def setup_terminal_logging():
    """
    모든 터미널 출력을 data/logs 폴더의 파일로 저장하도록 설정합니다.
    """
    # 현재 파일(logger.py)의 절대 경로를 기준으로 data 폴더 위치를 계산합니다.
    base_directory = os.path.dirname(os.path.abspath(__file__))
    log_directory = os.path.normpath(os.path.join(base_directory, "..", "data", "logs"))
    
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
        
    date_string = datetime.now().strftime("%Y%m%d")
    full_log_path = os.path.join(log_directory, f"terminal_full_{date_string}.log")
    
    # 표준 출력을 TerminalTee 클래스로 교체하여 파일 기록을 시작합니다.
    sys.stdout = TerminalTee(full_log_path)
    print(f"\n[SYSTEM] Log path initialized: {full_log_path}\n")

def get_logger(name):
    """
    모듈별 로깅 기능을 수행하는 로거 인스턴스를 생성합니다.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        logger.handlers.clear()
    
    stream_handler = logging.StreamHandler(sys.stdout)
    
    class LogFormatter(logging.Formatter):
        """로그 메시지의 형식을 지정하는 클래스입니다."""
        def format(self, record):
            time_str = datetime.now().strftime("%H:%M:%S")
            return f"[{time_str}] [{record.name.upper()}] {record.getMessage()}"
            
    stream_handler.setFormatter(LogFormatter())
    logger.addHandler(stream_handler)
    return logger