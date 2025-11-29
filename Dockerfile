# 라즈베리파이4 (ARM64)용 Dockerfile
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (필요한 의존성)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY *.py ./

# chroma_db 디렉토리 복사 (이미 크롤링된 DB 포함)
# .dockerignore에서 chroma_db 제외를 주석 처리했으므로 이미지에 포함됨
# chroma_db가 없으면 빌드 실패하므로, 먼저 크롤링을 실행하거나
# transfer_to_pi.sh 스크립트로 별도 전송도 가능
RUN mkdir -p /app/chroma_db
COPY chroma_db /app/chroma_db

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false
ENV PYTHONDONTWRITEBYTECODE=1

# 기본 명령어 (API 서버 실행)
CMD ["python", "api_server.py"]

