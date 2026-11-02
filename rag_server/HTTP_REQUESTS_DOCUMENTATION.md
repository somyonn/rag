# query.py와 ChromaDB 간 HTTP 요청/응답 명세서

이 문서는 `query.py`가 ChromaDB 서버와 주고받는 모든 HTTP 요청과 응답을 상세히 설명합니다.

## 기본 정보

- **서버 주소**: `http://192.168.1.102:8000` (또는 `CHROMA_SERVER_HOST:8000`)
- **API 버전**: `/api/v2`
- **기본 Tenant**: `default_tenant`
- **기본 Database**: `default_database`
- **컬렉션 이름**: `rag_documents` (또는 `CHROMA_COLLECTION_NAME`)

---

## 1. 컬렉션 조회 (Collection Get)

**발생 시점**: `vectorstore = Chroma(client=client, collection_name=CHROMA_COLLECTION_NAME, ...)` 실행 시

### 요청

```http
GET http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/rag_documents
Headers:
  Content-Type: application/json
  User-Agent: Chroma Python Client v1.3.4 (https://github.com/chroma-core/chroma)
```

### 응답

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "rag_documents",
  "metadata": null,
  "dimension": 768,
  "tenant": "default_tenant",
  "database": "default_database",
  "version": 1
}
```

---

## 2. 문서 개수 조회 (Count)

**발생 시점**: `collection.count()` 호출 시 (query.py 88번째 줄)

### 요청

```http
GET http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/count
Headers:
  Content-Type: application/json
  User-Agent: Chroma Python Client v1.3.4 (https://github.com/chroma-core/chroma)
```

### 응답

```json
1234
```

(단순 정수 값, 문서 개수)

---

## 3. 유사도 검색 (Query) - max_marginal_relevance_search

**발생 시점**: `vectorstore.max_marginal_relevance_search(query, k=k*5, fetch_k=k*20, lambda_mult=0.5)` 호출 시 (query.py 101번째 줄)

**참고**: `max_marginal_relevance_search`는 내부적으로 여러 번의 `similarity_search`를 호출합니다. 각 호출마다 아래와 같은 요청이 발생합니다.

### 요청

```http
POST http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
Headers:
  Content-Type: application/json
  User-Agent: Chroma Python Client v1.3.4 (https://github.com/chroma-core/chroma)
Body:
{
  "query_embeddings": [
    [0.123, 0.456, 0.789, ..., 0.321]  // 768차원 임베딩 벡터 (float 배열)
  ],
  "n_results": 100,  // fetch_k 값 (k*20, 예: k=5면 100)
  "where": null,  // 메타데이터 필터 조건 (없으면 null)
  "where_document": null,  // 문서 내용 필터 조건 (없으면 null)
  "include": ["metadatas", "documents", "distances"]  // 반환할 데이터 타입
}
```

### 응답

```json
{
  "ids": [
    [
      "doc-id-1",
      "doc-id-2",
      "doc-id-3",
      ...
      "doc-id-100"
    ]
  ],
  "distances": [
    [
      0.234,
      0.456,
      0.678,
      ...
      0.890
    ]
  ],
  "metadatas": [
    [
      {
        "url": "https://docs.aws.amazon.com/...",
        "title": "AWS Documentation",
        "source": "https://docs.aws.amazon.com/...",
        "source_type": "aws"
      },
      {
        "url": "https://docs.docker.com/...",
        "title": "Docker Documentation",
        "source": "https://docs.docker.com/...",
        "source_type": "docker"
      },
      ...
    ]
  ],
  "documents": [
    [
      "문서 내용 1...",
      "문서 내용 2...",
      "문서 내용 3...",
      ...
      "문서 내용 100..."
    ]
  ],
  "embeddings": null  // include에 포함되지 않으면 null
}
```

**응답 구조 설명**:
- `ids`: 각 쿼리 임베딩에 대한 결과 ID 배열 (2차원 배열: [쿼리별][결과별])
- `distances`: 코사인 거리 배열 (낮을수록 유사, 0~2 범위)
- `metadatas`: 메타데이터 배열 (각 문서의 메타데이터)
- `documents`: 문서 내용 배열 (각 문서의 텍스트)
- `embeddings`: 임베딩 벡터 (include에 포함되지 않으면 null)

---

## 4. 유사도 검색 (Query) - similarity_search

**발생 시점**: `vectorstore.similarity_search(doc.page_content[:50], k=1000)` 호출 시 (query.py 167번째 줄)

### 요청

```http
POST http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
Headers:
  Content-Type: application/json
  User-Agent: Chroma Python Client v1.3.4 (https://github.com/chroma-core/chroma)
Body:
{
  "query_embeddings": [
    [0.123, 0.456, 0.789, ..., 0.321]  // 문서 내용의 앞부분(50자) 임베딩 벡터
  ],
  "n_results": 1000,  // k 값
  "where": null,
  "where_document": null,
  "include": ["metadatas", "documents", "distances"]
}
```

### 응답

```json
{
  "ids": [
    [
      "doc-id-1",
      "doc-id-2",
      ...
      "doc-id-1000"
    ]
  ],
  "distances": [
    [
      0.123,
      0.234,
      ...
      0.999
    ]
  ],
  "metadatas": [
    [
      {
        "url": "...",
        "title": "...",
        "source": "...",
        ...
      },
      ...
    ]
  ],
  "documents": [
    [
      "문서 내용 1...",
      "문서 내용 2...",
      ...
      "문서 내용 1000..."
    ]
  ],
  "embeddings": null
}
```

---

## 요청 흐름 예시

`query.py`를 실행하면 다음과 같은 순서로 HTTP 요청이 발생합니다:

### 시나리오: `python query.py "AWS EC2 인스턴스" -k 5`

1. **컬렉션 조회** (GET)
   ```
   GET /api/v2/tenants/default_tenant/databases/default_database/collections/rag_documents
   ```

2. **문서 개수 확인** (GET)
   ```
   GET /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/count
   ```

3. **MMR 검색 - 1차 쿼리** (POST)
   ```
   POST /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
   Body: {
     "query_embeddings": [[...]],  // "AWS EC2 인스턴스" 임베딩
     "n_results": 100,  // fetch_k = 5*20
     ...
   }
   ```

4. **MMR 검색 - 2차 쿼리** (POST, 내부적으로 여러 번 호출될 수 있음)
   ```
   POST /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
   Body: {
     "query_embeddings": [[...]],  // 첫 번째 결과 문서 임베딩
     "n_results": 100,
     ...
   }
   ```
   (MMR 알고리즘에 따라 여러 번 반복)

5. **URL별 청크 수집** (POST, 각 URL마다)
   ```
   POST /api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query
   Body: {
     "query_embeddings": [[...]],  // 문서 내용 앞부분(50자) 임베딩
     "n_results": 1000,
     ...
   }
   ```
   (각 결과 문서의 URL마다 최대 1번씩 호출)

---

## HTTP 상태 코드

- **200 OK**: 요청 성공
- **400 Bad Request**: 잘못된 요청 (예: 잘못된 파라미터)
- **404 Not Found**: 컬렉션이나 리소스를 찾을 수 없음
- **500 Internal Server Error**: 서버 내부 오류

---

## 에러 응답 형식

에러 발생 시 응답 형식:

```json
{
  "error": "Error message here",
  "error_type": "ErrorType",
  "status_code": 400
}
```

---

## 참고사항

1. **임베딩 벡터**: 모든 쿼리는 768차원 임베딩 벡터를 사용합니다 (jhgan/ko-sroberta-nli 모델)
2. **거리 계산**: ChromaDB는 코사인 거리를 사용합니다 (0~2 범위, 낮을수록 유사)
3. **배치 처리**: `query_embeddings`는 배열로 여러 쿼리를 한 번에 처리할 수 있지만, 현재 코드는 단일 쿼리를 사용합니다
4. **HTTP/1.1**: 현재는 HTTP/1.1을 사용하며, HTTP/2를 사용하려면 `grpc_query.py`를 참고하세요

---

## 실제 요청 예시 (curl)

### 컬렉션 조회
```bash
curl -X GET \
  "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/rag_documents" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Chroma Python Client v1.3.4"
```

### 문서 개수 조회
```bash
curl -X GET \
  "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/count" \
  -H "Content-Type: application/json"
```

### 유사도 검색
```bash
curl -X POST \
  "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query_embeddings": [[0.123, 0.456, ...]],
    "n_results": 100,
    "where": null,
    "where_document": null,
    "include": ["metadatas", "documents", "distances"]
  }'
```

