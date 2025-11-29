"""RAG 시스템 HTTP API 서버.

다른 노드에서 HTTP 요청을 통해 RAG 시스템을 사용할 수 있도록 합니다.
"""

import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag import get_rag_pipeline, RAGPipeline

# 환경 변수 설정
HOST = os.getenv("RAG_API_HOST", "0.0.0.0")  # 모든 인터페이스에서 접근 가능
PORT = int(os.getenv("RAG_API_PORT", "8000"))
PERSIST_DIRECTORY = os.getenv("RAG_PERSIST_DIRECTORY", "./chroma_db")
LLM_TYPE = os.getenv("LLM_TYPE", "openai")
K = int(os.getenv("RAG_K", "5"))
MIN_SIMILARITY_THRESHOLD = float(os.getenv("RAG_MIN_SIMILARITY", "0.3"))
VERBOSE = os.getenv("RAG_VERBOSE", "false").lower() == "true"

# FastAPI 앱 생성
app = FastAPI(
    title="RAG System API",
    description="Retrieval-Augmented Generation System HTTP API",
    version="1.0.0",
)

# CORS 설정 (다른 노드에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하도록 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG 파이프라인 전역 인스턴스
rag_pipeline: Optional[RAGPipeline] = None


# 요청/응답 모델
class QueryRequest(BaseModel):
    """질문 요청 모델."""
    question: str = Field(..., description="질문 내용")
    k: Optional[int] = Field(None, description="검색할 문서 개수 (기본값: 5)")
    return_documents: Optional[bool] = Field(False, description="검색된 문서도 반환할지 여부")
    min_similarity_threshold: Optional[float] = Field(None, description="최소 유사도 임계값")


class DocumentInfo(BaseModel):
    """문서 정보 모델."""
    title: str
    url: str
    content: str
    source_type: Optional[str] = None


class TimingInfo(BaseModel):
    """시간 측정 정보 모델."""
    retrieval_time: float = Field(..., description="문서 검색 소요 시간 (초)")
    generation_time: float = Field(..., description="답변 생성 소요 시간 (초)")
    total_time: float = Field(..., description="전체 소요 시간 (초)")


class QueryResponse(BaseModel):
    """질문 응답 모델."""
    question: str
    answer: str
    documents: Optional[List[DocumentInfo]] = None
    timing: Optional[TimingInfo] = Field(None, description="각 단계별 소요 시간")


class HealthResponse(BaseModel):
    """헬스 체크 응답 모델."""
    status: str
    message: str
    chroma_db_exists: bool


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 RAG 파이프라인 초기화."""
    global rag_pipeline
    try:
        print(f"\n[RAG API 서버] 초기화 중...")
        print(f"  - ChromaDB 경로: {PERSIST_DIRECTORY}")
        print(f"  - LLM 타입: {LLM_TYPE}")
        print(f"  - K: {K}")
        print(f"  - 최소 유사도: {MIN_SIMILARITY_THRESHOLD}")
        
        rag_pipeline = get_rag_pipeline(
            persist_directory=PERSIST_DIRECTORY,
            k=K,
            min_similarity_threshold=MIN_SIMILARITY_THRESHOLD,
            llm_type=LLM_TYPE,
            verbose=VERBOSE,
        )
        print(f"[RAG API 서버] 초기화 완료!")
    except Exception as e:
        print(f"[RAG API 서버] 초기화 실패: {e}")
        raise


@app.get("/", response_model=Dict[str, str])
async def root():
    """루트 엔드포인트."""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트."""
    chroma_db_exists = os.path.exists(PERSIST_DIRECTORY)
    status = "healthy" if (rag_pipeline is not None and chroma_db_exists) else "unhealthy"
    message = "RAG 시스템이 정상적으로 작동 중입니다." if status == "healthy" else "RAG 시스템 초기화 실패 또는 ChromaDB가 없습니다."
    
    return HealthResponse(
        status=status,
        message=message,
        chroma_db_exists=chroma_db_exists,
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """질문에 대한 답변을 생성하는 엔드포인트.
    
    Args:
        request: 질문 요청
        
    Returns:
        질문에 대한 답변과 (선택적으로) 검색된 문서
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG 파이프라인이 초기화되지 않았습니다.")
    
    try:
        # 요청 파라미터 적용
        k = request.k if request.k is not None else K
        min_similarity = request.min_similarity_threshold if request.min_similarity_threshold is not None else MIN_SIMILARITY_THRESHOLD
        
        # RAG 파이프라인 실행
        result = rag_pipeline.query(
            question=request.question,
            return_documents=request.return_documents,
        )
        
        # 문서 정보 변환
        documents = None
        if request.return_documents and "documents" in result:
            documents = []
            for doc in result["documents"]:
                documents.append(DocumentInfo(
                    title=doc.metadata.get("title", ""),
                    url=doc.metadata.get("url") or doc.metadata.get("source", ""),
                    content=doc.page_content,
                    source_type=doc.metadata.get("source_type"),
                ))
        
        # 시간 정보 추출
        timing_info = None
        if "timing" in result:
            timing = result["timing"]
            timing_info = TimingInfo(
                retrieval_time=timing.get("retrieval_time", 0),
                generation_time=timing.get("generation_time", 0),
                total_time=timing.get("total_time", 0),
            )
        
        return QueryResponse(
            question=result.get("question", request.question),
            answer=result.get("answer", ""),
            documents=documents,
            timing=timing_info,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 생성 중 오류 발생: {str(e)}")


@app.get("/info", response_model=Dict[str, Any])
async def get_info():
    """시스템 정보를 반환하는 엔드포인트."""
    return {
        "host": HOST,
        "port": PORT,
        "persist_directory": PERSIST_DIRECTORY,
        "llm_type": LLM_TYPE,
        "k": K,
        "min_similarity_threshold": MIN_SIMILARITY_THRESHOLD,
        "chroma_db_exists": os.path.exists(PERSIST_DIRECTORY),
        "rag_pipeline_initialized": rag_pipeline is not None,
    }


if __name__ == "__main__":
    import uvicorn
    print(f"\n[RAG API 서버] 시작 중...")
    print(f"  - 주소: http://{HOST}:{PORT}")
    print(f"  - API 문서: http://{HOST}:{PORT}/docs")
    print(f"  - 헬스 체크: http://{HOST}:{PORT}/health")
    print(f"\n다른 노드에서 접근: http://192.168.1.102:{PORT}\n")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )

