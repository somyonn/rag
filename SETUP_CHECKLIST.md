# RAG 시스템 Docker 설정 체크리스트

라즈베리파이4에서 실행하기 전에 확인해야 할 사항들입니다.

## ✅ 필수 설정 항목

### 1. 환경 변수 파일 (.env) 생성

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

```bash
# LLM 타입 선택 (openai 또는 huggingface)
LLM_TYPE=openai

# OpenAI 사용 시 (권장)
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# HuggingFace 사용 시 (선택)
# HUGGINGFACE_API_TOKEN=your-actual-huggingface-token-here
# HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

**⚠️ 중요**: `your_openai_api_key_here` 부분을 실제 API 키로 교체해야 합니다!

### 2. 크롤링 데이터 준비

RAG 시스템이 작동하려면 크롤링된 데이터베이스가 필요합니다:

```bash
# 로컬에서 크롤링 실행
python crawl_and_update.py

# 또는 Docker 내에서 실행
docker run --rm \
  -v $(pwd)/chroma_db:/app/chroma_db \
  rag-system:latest \
  python crawl_and_update.py
```

**⚠️ 중요**: `chroma_db` 디렉토리가 생성되고 데이터가 있어야 합니다!

### 3. 라즈베리파이 IP 주소 확인

`transfer_to_pi.sh` 스크립트 실행 시 라즈베리파이 IP 주소가 필요합니다:

```bash
# 라즈베리파이에서 IP 확인
hostname -I

# 또는
ip addr show
```

예시: `pi@192.168.1.100`

## 📋 선택적 설정

### Docker Hub 사용 (선택)

Docker Hub에 이미지를 푸시하려면:

```bash
# Docker Hub 로그인
docker login

# 이미지 태그
docker tag rag-system:latest your-username/rag-system:latest

# 푸시
docker push your-username/rag-system:latest
```

### 포트 매핑 (API 서버 사용 시)

`docker-compose.yml`에서 포트 매핑을 활성화하려면 주석을 해제하세요:

```yaml
ports:
  - "8000:8000"
```

## 🔍 확인 사항

실행 전에 다음을 확인하세요:

- [ ] `.env` 파일이 생성되었고 API 키가 올바르게 설정되었는가?
- [ ] `chroma_db` 디렉토리가 존재하고 데이터가 있는가?
- [ ] 라즈베리파이에 Docker가 설치되어 있는가?
- [ ] 라즈베리파이 IP 주소를 알고 있는가?

## 🚀 빠른 시작

1. **로컬에서 빌드**:
   ```bash
   ./build.sh
   ```

2. **크롤링 실행** (데이터 준비):
   ```bash
   python crawl_and_update.py
   ```

3. **라즈베리파이로 전송**:
   ```bash
   ./transfer_to_pi.sh pi@192.168.1.102
   ```

4. **라즈베리파이에서 실행**:
   ```bash
   docker load < rag-system.tar.gz
   tar -xzf rag-files.tar.gz
   # .env 파일 생성 및 API 키 설정
   docker-compose up -d
   ```

5. **HTTP API 서버 접근**:
   - 로컬: `http://localhost:8000`
   - 다른 노드: `http://192.168.1.102:8000`
   - API 문서: `http://192.168.1.102:8000/docs`

## 📡 HTTP API 사용

RAG 시스템은 HTTP API 서버로 실행됩니다. 다른 노드에서 다음과 같이 사용할 수 있습니다:

```bash
# 질문하기
curl -X POST http://192.168.1.102:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "AWS Lambda는 무엇인가요?"}'
```

자세한 사용법은 `API_USAGE.md`를 참고하세요.

