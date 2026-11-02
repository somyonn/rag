# 분산화 RAG 시스템 (캡스톤디자인, 2025-2)

AWS와 Docker 공식 문서를 근거로 질문에 답하는 RAG 서비스입니다. 3인 팀 프로젝트(2025.09 ~ 2025.12)이며, 이 저장소는 **제가 맡은 문서 수집, 벡터 DB, 검색 부분**을 모아 둔 개인 저장소입니다.

- 팀 저장소는 비공개입니다. 이 저장소의 첫 커밋(2025-11-29 `init`)이 팀 저장소의 시작 코드이고, 이후 리팩터링과 기능 추가는 팀 저장소에서 진행했습니다.

## 구조

질문 전처리와 문서 검색은 엣지 디바이스(라즈베리파이 4)에서, 답변 생성은 LLM 서버에서 처리하도록 나눴습니다.

```
질문 → [엣지: 임베딩 → ChromaDB MMR 검색 → 프롬프트 완성] → [LLM 서버: 답변 생성]
```

## 제가 한 일

| 부분 | 파일 | 내용 |
|---|---|---|
| 문서 수집 | `urls.py`, `collect.py` | Docker 문서 1,213개, AWS 문서 865개 등 약 2,090개 주소 |
| 정제와 청킹 | `crawl_and_update.py` | 사이트별 본문 추출, 네비게이션 조각 제거, 600토큰 단위 분할(겹침 200) |
| 임베딩과 벡터 DB | `crawl_and_update.py` | `jhgan/ko-sroberta-nli`(768차원) 임베딩, ChromaDB 저장 |
| 검색 | `retriever.py`, `query.py` | MMR 검색(관련성 우선 `lambda_mult=0.2`), 중복 제거 |
| 서빙 | `api_server.py`, `rag.py`, `generator.py` | FastAPI `/query`, `/health`, `/info` |
| 엣지 배포 | `Dockerfile`, `build.sh`, `transfer_to_pi.sh` | Docker 이미지를 라즈베리파이로 옮겨 실행 |
| ChromaDB 서버 모드 | `rag_server/` | ChromaDB를 Docker 서버로 띄우고 gRPC로 연결, 팀원용 통신 가이드 |

팀원이 맡은 부분(이 저장소에 없음): LangGraph 워크플로우, 시맨틱 캐싱, 웹 클라이언트, 문서 캐시.

## 실행

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...        # 답변 생성용
python crawl_and_update.py       # 문서 수집과 벡터 DB 생성
python api_server.py             # http://localhost:8000
```

자세한 내용은 `API_USAGE.md`, `DOCKER_GUIDE.md`, `SETUP_CHECKLIST.md`를 참고하세요.
