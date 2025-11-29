# RAG API 사용 가이드

라즈베리파이4에서 실행되는 RAG 시스템의 HTTP API 사용 방법입니다.

## 서버 주소

- **로컬 접근**: `http://localhost:8000`
- **다른 노드에서 접근**: `http://192.168.1.102:8000`

## API 엔드포인트

### 1. 루트 (`GET /`)

서버 정보를 반환합니다.

```bash
curl http://192.168.1.102:8000/
```

**응답 예시:**
```json
{
  "message": "RAG System API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

### 2. 헬스 체크 (`GET /health`)

서버 상태를 확인합니다.

```bash
curl http://192.168.1.102:8000/health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "message": "RAG 시스템이 정상적으로 작동 중입니다.",
  "chroma_db_exists": true
}
```

### 3. 질문하기 (`POST /query`)

질문에 대한 답변을 생성합니다.

```bash
curl -X POST http://192.168.1.102:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "AWS Lambda는 무엇인가요?",
    "k": 5,
    "return_documents": true
  }'
```

**요청 파라미터:**
- `question` (필수): 질문 내용
- `k` (선택): 검색할 문서 개수 (기본값: 5)
- `return_documents` (선택): 검색된 문서도 반환할지 여부 (기본값: false)
- `min_similarity_threshold` (선택): 최소 유사도 임계값 (기본값: 0.3)

**응답 예시:**
```json
{
  "question": "AWS Lambda는 무엇인가요?",
  "answer": "AWS Lambda는 서버리스 컴퓨팅 서비스로...",
  "documents": [
    {
      "title": "AWS Lambda 소개",
      "url": "https://docs.aws.amazon.com/lambda/...",
      "content": "AWS Lambda는...",
      "source_type": "aws"
    }
  ],
  "timing": {
    "retrieval_time": 0.543,
    "generation_time": 1.234,
    "total_time": 1.777
  }
}
```

**시간 측정 정보:**
- `retrieval_time`: 문서 검색 단계 소요 시간 (초)
- `generation_time`: 답변 생성 단계 소요 시간 (초)
- `total_time`: 전체 파이프라인 소요 시간 (초)

### 4. 시스템 정보 (`GET /info`)

시스템 설정 정보를 반환합니다.

```bash
curl http://192.168.1.102:8000/info
```

**응답 예시:**
```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "persist_directory": "./chroma_db",
  "llm_type": "openai",
  "k": 5,
  "min_similarity_threshold": 0.3,
  "chroma_db_exists": true,
  "rag_pipeline_initialized": true
}
```

### 5. API 문서 (`GET /docs`)

Swagger UI를 통해 인터랙티브한 API 문서를 확인할 수 있습니다.

브라우저에서 접근:
```
http://192.168.1.102:8000/docs
```

## Python 클라이언트 예시

```python
import requests

# API 서버 주소
API_URL = "http://192.168.1.102:8000"

# 질문하기
response = requests.post(
    f"{API_URL}/query",
    json={
        "question": "Docker 컨테이너는 무엇인가요?",
        "k": 5,
        "return_documents": True,
    }
)

result = response.json()
print(f"질문: {result['question']}")
print(f"답변: {result['answer']}")
print(f"\n참고 문서:")
for doc in result.get('documents', []):
    print(f"  - {doc['title']}: {doc['url']}")
print(f"\n소요 시간:")
if 'timing' in result:
    timing = result['timing']
    print(f"  - 문서 검색: {timing['retrieval_time']:.3f}초")
    print(f"  - 답변 생성: {timing['generation_time']:.3f}초")
    print(f"  - 전체 소요: {timing['total_time']:.3f}초")
```

## JavaScript/Node.js 클라이언트 예시

```javascript
const axios = require('axios');

const API_URL = 'http://192.168.1.102:8000';

async function query(question) {
  try {
    const response = await axios.post(`${API_URL}/query`, {
      question: question,
      k: 5,
      return_documents: true,
    });
    
    console.log('질문:', response.data.question);
    console.log('답변:', response.data.answer);
    console.log('\n참고 문서:');
    response.data.documents?.forEach(doc => {
      console.log(`  - ${doc.title}: ${doc.url}`);
    });
    console.log('\n소요 시간:');
    if (response.data.timing) {
      console.log(`  - 문서 검색: ${response.data.timing.retrieval_time.toFixed(3)}초`);
      console.log(`  - 답변 생성: ${response.data.timing.generation_time.toFixed(3)}초`);
      console.log(`  - 전체 소요: ${response.data.timing.total_time.toFixed(3)}초`);
    }
  } catch (error) {
    console.error('오류:', error.message);
  }
}

query('AWS Lambda는 무엇인가요?');
```

## 환경 변수 설정

API 서버는 다음 환경 변수를 지원합니다:

- `RAG_API_HOST`: 서버 호스트 (기본값: `0.0.0.0`)
- `RAG_API_PORT`: 서버 포트 (기본값: `8000`)
- `RAG_PERSIST_DIRECTORY`: ChromaDB 경로 (기본값: `./chroma_db`)
- `LLM_TYPE`: LLM 타입 (기본값: `openai`)
- `RAG_K`: 기본 검색 문서 개수 (기본값: `5`)
- `RAG_MIN_SIMILARITY`: 기본 최소 유사도 (기본값: `0.3`)
- `RAG_VERBOSE`: 상세 출력 여부 (기본값: `false`)

## Docker Compose로 실행

```bash
# 서버 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서버 중지
docker-compose down
```

## 문제 해결

### 연결이 안 될 때

1. **방화벽 확인**: 라즈베리파이의 8000 포트가 열려있는지 확인
   ```bash
   sudo ufw allow 8000
   ```

2. **서버 상태 확인**: 헬스 체크 엔드포인트로 확인
   ```bash
   curl http://192.168.1.102:8000/health
   ```

3. **Docker 컨테이너 확인**: 컨테이너가 실행 중인지 확인
   ```bash
   docker ps
   docker-compose logs
   ```

### ChromaDB가 없다는 오류

크롤링을 먼저 실행해야 합니다:

```bash
docker-compose exec rag python crawl_and_update.py
```

또는 로컬에서:

```bash
python crawl_and_update.py
```

