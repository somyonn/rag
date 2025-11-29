# RAG 시스템 Docker 가이드

라즈베리파이4에서 RAG 시스템을 Docker로 실행하는 방법입니다.

## 사전 요구사항

- 라즈베리파이4 (ARM64 또는 ARMv7)
- Docker 및 Docker Compose 설치
- 최소 4GB RAM 권장

## Docker 설치 (라즈베리파이)

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

## 빌드 및 실행

### 1. 이미지 빌드

```bash
# ARM64용 빌드
docker build -t rag-system:latest .

# 또는 특정 플랫폼 지정
docker build --platform linux/arm64 -t rag-system:latest .
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# .env 파일
OPENAI_API_KEY=your_openai_api_key
# 또는
HUGGINGFACE_API_TOKEN=your_huggingface_token
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
LLM_TYPE=openai  # 또는 huggingface
```

### 3. Docker Compose로 실행

```bash
# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 4. 직접 Docker로 실행

```bash
# RAG 질의 실행
docker run --rm \
  -v $(pwd)/chroma_db:/app/chroma_db \
  --env-file .env \
  rag-system:latest \
  python rag.py "질문 내용"

# 대화형 모드
docker run -it --rm \
  -v $(pwd)/chroma_db:/app/chroma_db \
  --env-file .env \
  rag-system:latest \
  /bin/bash
```

## 데이터베이스 준비

크롤링된 데이터베이스가 필요합니다:

```bash
# 로컬에서 크롤링 실행
python crawl_and_update.py

# 또는 Docker 내에서 실행
docker run --rm \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/urls.py:/app/urls.py \
  rag-system:latest \
  python crawl_and_update.py
```

## 볼륨 마운트

`chroma_db` 디렉토리는 볼륨으로 마운트하여 데이터를 영구 저장합니다:

```yaml
volumes:
  - ./chroma_db:/app/chroma_db
```

## 성능 최적화

라즈베리파이4의 제한된 리소스를 고려:

1. **메모리 제한 설정**:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
```

2. **CPU 제한**:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
```

## 문제 해결

### 빌드 실패
- ARM 아키텍처 확인: `uname -m`
- 플랫폼 명시: `--platform linux/arm64`

### 메모리 부족
- requirements.txt에서 불필요한 패키지 제거
- 더 작은 모델 사용

### 느린 성능
- CPU 코어 수 확인
- 메모리 할당 증가

## 전송 방법

라즈베리파이로 전송:

```bash
# 1. 이미지를 tar 파일로 저장
docker save rag-system:latest | gzip > rag-system.tar.gz

# 2. 라즈베리파이로 전송
scp rag-system.tar.gz pi@raspberrypi:/home/pi/

# 3. 라즈베리파이에서 로드
ssh pi@raspberrypi
docker load < rag-system.tar.gz
```

또는:

```bash
# Docker Hub에 푸시 (라즈베리파이에서 pull)
docker tag rag-system:latest your-username/rag-system:latest
docker push your-username/rag-system:latest
```


