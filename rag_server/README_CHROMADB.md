# ChromaDB 서버 모드 설정 가이드

이 프로젝트는 ChromaDB를 Docker 위에서 서버 모드로 실행하고 gRPC를 통해 통신하도록 설정되어 있습니다.

## 사전 요구사항

- Docker 및 Docker Compose 설치
- Python 3.8 이상
- 필요한 Python 패키지 설치 (`requirements.txt`)

## 설정 방법

### 1. ChromaDB 서버 시작

Docker Compose를 사용하여 ChromaDB 서버를 시작합니다:

```bash
docker-compose up -d
```

서버가 정상적으로 시작되었는지 확인:

```bash
docker-compose ps
docker-compose logs chromadb
```

### 2. 환경 변수 설정 (선택사항)

기본 설정으로도 동작하지만, 필요시 환경 변수를 설정할 수 있습니다:

```bash
export CHROMA_SERVER_HOST=localhost
export CHROMA_SERVER_HTTP_PORT=8000
export CHROMA_SERVER_GRPC_PORT=50051
export CHROMA_SERVER_AUTH_TOKEN=test-token
export CHROMA_COLLECTION_NAME=rag_documents
export USE_SERVER_MODE=true
```

또는 `.env` 파일을 생성하여 설정할 수 있습니다 (`.env.example` 참고).

### 3. 데이터베이스 초기화

크롤링 및 데이터베이스 업데이트:

```bash
python crawl_and_update.py --aws
# 또는
python crawl_and_update.py --docker
```

### 4. 검색 테스트

```bash
python query.py "검색할 질의" -k 5
```

## 서버 모드 vs 로컬 모드

### 서버 모드 (기본값)

- `USE_SERVER_MODE=true`로 설정
- Docker에서 실행 중인 ChromaDB 서버에 연결
- gRPC를 통해 통신 (포트 50051)
- HTTP API도 사용 가능 (포트 8000)
- 여러 클라이언트가 동시에 접근 가능

### 로컬 모드

- `USE_SERVER_MODE=false`로 설정
- 로컬 파일 시스템에 직접 저장 (`./chroma_db`)
- 단일 프로세스에서만 사용 가능

## Docker Compose 명령어

```bash
# 서버 시작
docker-compose up -d

# 서버 중지
docker-compose down

# 서버 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f chromadb

# 서버 상태 확인
docker-compose ps
```

## 포트 정보

- **8000**: HTTP API 포트
- **50051**: gRPC 포트

## 데이터 영속성

ChromaDB 데이터는 `./chroma_db` 디렉토리에 Docker 볼륨으로 마운트되어 영속적으로 저장됩니다.

## 문제 해결

### 서버 연결 실패

1. Docker 컨테이너가 실행 중인지 확인:
   ```bash
   docker-compose ps
   ```

2. 서버 로그 확인:
   ```bash
   docker-compose logs chromadb
   ```

3. 포트가 사용 중인지 확인:
   ```bash
   lsof -i :8000
   lsof -i :50051
   ```

### 인증 오류

`CHROMA_SERVER_AUTH_TOKEN`이 `docker-compose.yml`의 `CHROMA_SERVER_AUTHN_CREDENTIALS`와 일치하는지 확인하세요.

## 참고사항

- ChromaDB 서버는 기본적으로 gRPC와 HTTP를 모두 지원합니다.
- 클라이언트는 HTTP API를 통해 연결하지만, 내부적으로 최적의 프로토콜을 사용합니다.
- 서버 모드에서 연결 실패 시 자동으로 로컬 모드로 폴백됩니다.

