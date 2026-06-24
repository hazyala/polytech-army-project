@echo off
:: 1. 아나콘다 경로 설정
SET CONDA_PATH=C:\Users\AISW-509-208\anaconda3\condabin\conda.bat

:: 2. 가상환경 활성화 
call %CONDA_PATH% activate pybullet_env

:: 3. 메인 시뮬레이션 및 서버 실행
start python main.py

:: 4. 서버가 완전히 켜질 때까지 대기
timeout /t 3

:: 5. Web UI 실행
start http://localhost:8501
python -m streamlit run app.py --server.headless true --browser.gatherUsageStats false

pause