# ChromaDB 통신 가이드 (협업자용)

이 문서는 RAG 서버 프로젝트에서 ChromaDB와 통신하기 위해 필요한 모든 정보를 담고 있습니다.

## 📋 필수 정보

### 1. 서버 연결 정보

**기본 설정 (로컬 개발):**
- **서버 주소**: `localhost` (또는 `127.0.0.1`)
- **HTTP 포트**: `8000`
- **gRPC 포트**: `50051`
- **API 버전**: `/api/v2`

**원격 서버 사용 시:**
- **서버 주소**: ChromaDB 서버가 실행 중인 노드의 IP 주소 (예: `192.168.1.102`)
- **HTTP 포트**: `8000`
- **gRPC 포트**: `50051`

### 2. 컬렉션 정보

- **컬렉션 이름**: `rag_documents`
- **Tenant**: `default_tenant`
- **Database**: `default_database`

### 3. 인증 정보

**현재 설정**: 인증 없음 (기본값)

인증이 필요한 경우:
- **인증 토큰**: 서버 관리자에게 문의
- 환경 변수로 설정: `CHROMA_SERVER_AUTH_TOKEN=your-token`

---

## 🔧 환경 설정 방법

### 방법 1: 환경 변수 설정 (권장)

```bash
# ChromaDB 서버 주소 설정
export CHROMA_SERVER_HOST=192.168.1.102  # 원격 서버 IP 또는 localhost

# 포트 설정 (기본값 사용 시 생략 가능)
export CHROMA_SERVER_HTTP_PORT=8000
export CHROMA_SERVER_GRPC_PORT=50051

# 컬렉션 이름 (기본값 사용 시 생략 가능)
export CHROMA_COLLECTION_NAME=rag_documents

# 서버 모드 사용 (기본값: true)
export USE_SERVER_MODE=true

# 인증 토큰 (인증이 필요한 경우)
export CHROMA_SERVER_AUTH_TOKEN=your-token-here
```

### 방법 2: .env 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```bash
CHROMA_SERVER_HOST=192.168.1.102
CHROMA_SERVER_HTTP_PORT=8000
CHROMA_SERVER_GRPC_PORT=50051
CHROMA_COLLECTION_NAME=rag_documents
USE_SERVER_MODE=true
CHROMA_SERVER_AUTH_TOKEN=
```

### 방법 3: config.py 직접 수정

`config.py` 파일의 기본값 수정:

```python
CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "192.168.1.102")  # 기본값 변경
```

---

## 🚀 사용 방법

### 1. 프로젝트 설정

```bash
# 1. 프로젝트 디렉토리로 이동
cd rag_server

# 2. 가상 환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt
```

### 2. ChromaDB 서버 확인

**로컬에서 서버 실행 중인 경우:**
```bash
# Docker Compose로 서버 시작
docker-compose up -d

# 서버 상태 확인
docker-compose ps
curl http://localhost:8000/api/v2/heartbeat
```

**원격 서버 사용 시:**
```bash
# 서버 연결 테스트
curl http://192.168.1.102:8000/api/v2/heartbeat
```

### 3. 검색 실행

```bash
# 기본 검색
python query.py "검색할 질의" -k 5

# HTTP/2 사용 (grpc_query.py)
python grpc_query.py "검색할 질의" -k 5
```

---

## 📡 API 엔드포인트 정보

### 기본 URL 구조

```
http://{CHROMA_SERVER_HOST}:{CHROMA_SERVER_HTTP_PORT}/api/v2/tenants/{tenant}/databases/{database}/collections/{collection_name}
```

### 주요 엔드포인트

#### 1. 컬렉션 조회
```http
GET /api/v2/tenants/default_tenant/databases/default_database/collections/rag_documents
```

#### 2. 문서 개수 조회
```http
GET /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/count
```

#### 3. 유사도 검색
```http
POST /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
Content-Type: application/json

{
  "query_embeddings": [[0.123, 0.456, ...]],  // 768차원 벡터
  "n_results": 100,
  "where": null,
  "where_document": null,
  "include": ["metadatas", "documents", "distances"]
}
```

자세한 API 문서는 `HTTP_REQUESTS_DOCUMENTATION.md` 참고

---

## 🔍 연결 확인 방법

### 1. 서버 상태 확인

```bash
# HTTP 헬스체크
curl http://localhost:8000/api/v2/heartbeat

# 또는
curl http://192.168.1.102:8000/api/v2/heartbeat
```

### 2. Python에서 연결 테스트

```python
from chromadb import HttpClient

client = HttpClient(host="192.168.1.102", port=8000)
print(client.heartbeat())  # 서버 시간 반환
```

### 3. 포트 확인

```bash
# HTTP 포트 확인
lsof -i :8000

# gRPC 포트 확인
lsof -i :50051
```

---

## ⚠️ 문제 해결

### 연결 실패 시

1. **서버 주소 확인**
   ```bash
   ping 192.168.1.102  # 서버 IP로 변경
   ```

2. **포트 확인**
   ```bash
   telnet 192.168.1.102 8000  # 서버 IP로 변경
   ```

3. **방화벽 확인**
   - HTTP 포트 8000이 열려있는지 확인
   - gRPC 포트 50051이 열려있는지 확인

4. **환경 변수 확인**
   ```bash
   echo $CHROMA_SERVER_HOST
   echo $CHROMA_SERVER_HTTP_PORT
   ```

### 인증 오류 시

1. 인증 토큰이 올바른지 확인
2. `docker-compose.yml`의 인증 설정과 일치하는지 확인
3. 환경 변수 `CHROMA_SERVER_AUTH_TOKEN` 설정 확인

### 데이터베이스 비어있음 오류

```bash
# 데이터베이스 초기화
python crawl_and_update.py --aws
# 또는
python crawl_and_update.py --docker
```

---

## 📝 코드에서 사용 예시

### query.py 사용

```python
from query import find_most_similar_document

# 검색 실행
results = find_most_similar_document("검색할 질의", k=5)
```

### 직접 ChromaDB 클라이언트 사용

```python
from chromadb import HttpClient
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# 클라이언트 생성
client = HttpClient(
    host="192.168.1.102",  # 서버 IP
    port=8000
)

# 임베딩 모델 설정
embeddings = SentenceTransformerEmbeddings(
    model_name='jhgan/ko-sroberta-nli',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True},
)

# Vectorstore 생성
vectorstore = Chroma(
    client=client,
    collection_name="rag_documents",
    embedding_function=embeddings,
)

# 검색
results = vectorstore.similarity_search("검색할 질의", k=5)
```

---

## 🔐 보안 고려사항

1. **인증 토큰**: 프로덕션 환경에서는 반드시 인증 토큰 사용
2. **네트워크**: 가능하면 VPN이나 사설 네트워크 사용
3. **방화벽**: 필요한 포트만 열기
4. **환경 변수**: 민감한 정보는 환경 변수로 관리, 코드에 하드코딩 금지

---

## 📞 문의 사항

- **서버 주소/IP**: 프로젝트 관리자에게 문의
- **인증 토큰**: 프로젝트 관리자에게 문의
- **컬렉션 이름**: `rag_documents` (기본값)
- **포트**: HTTP 8000, gRPC 50051 (기본값)

---

## 📚 추가 문서

- `HTTP_REQUESTS_DOCUMENTATION.md`: 상세한 HTTP 요청/응답 명세
- `README_CHROMADB.md`: ChromaDB 서버 설정 가이드
- `config.py`: 설정 파일 (기본값 확인)

