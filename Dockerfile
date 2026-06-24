# 1. 파이썬 3.10 버전의 가벼운 이미지(Slim)를 기반으로 합니다.
FROM python:3.10-slim

# 2. 작업 폴더를 설정합니다.
WORKDIR /Army_2D_Simulator_Proto

# 3. 비전 처리를 위한 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. 준비물 목록(requirements.txt)을 복사하고 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 현재 폴더의 모든 소스 코드를 컨테이너 안으로 복사합니다.
COPY . .

# 6. Streamlit이 사용하는 포트(8501)를 열어줍니다.
EXPOSE 8501

# 7. 컨테이너가 시작되면 Streamlit을 실행합니다.
CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0"]