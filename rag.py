"""RAG (Retrieval-Augmented Generation) 파이프라인.

Retriever와 Generator를 결합하여 완전한 RAG 시스템을 제공합니다.
"""

import os
import time
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document

from retriever import get_retriever, CustomChromaRetriever
from generator import get_generator, RAGGenerator


class RAGPipeline:
    """완전한 RAG 파이프라인.
    
    문서 검색(Retrieval)과 답변 생성(Generation)을 결합합니다.
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        retriever: Optional[CustomChromaRetriever] = None,
        generator: Optional[RAGGenerator] = None,
        k: int = 5,
        min_similarity_threshold: float = 0.3,
        llm_type: str = None,
        verbose: bool = True,
    ):
        """RAG 파이프라인 초기화.
        
        Args:
            persist_directory: ChromaDB 저장 경로
            retriever: Retriever 인스턴스 (None이면 자동 생성)
            generator: Generator 인스턴스 (None이면 자동 생성)
            k: 검색할 문서 개수
            min_similarity_threshold: 최소 유사도 임계값
            llm_type: LLM 타입 ("huggingface" or "openai")
            verbose: 상세 출력 여부
        """
        self.verbose = verbose
        
        # Retriever 초기화
        if retriever is None:
            self.retriever = get_retriever(
                persist_directory=persist_directory,
                k=k,
                min_similarity_threshold=min_similarity_threshold,
                verbose=verbose,
            )
        else:
            self.retriever = retriever
        
        # Generator 초기화
        if generator is None:
            self.generator = get_generator(
                llm_type=llm_type,
                verbose=verbose,
            )
        else:
            self.generator = generator
    
    def query(
        self,
        question: str,
        return_documents: bool = False,
    ) -> Dict[str, Any]:
        """질문에 대한 답변을 생성.
        
        Args:
            question: 질문
            return_documents: 검색된 문서도 함께 반환할지 여부
            
        Returns:
            답변과 (선택적으로) 검색된 문서를 포함한 딕셔너리
        """
        if self.verbose:
            print("\n" + "=" * 50)
            print("RAG 파이프라인 실행")
            print("=" * 50)
        
        # 전체 시작 시간
        total_start_time = time.time()
        
        # 1. 문서 검색
        if self.verbose:
            print("\n[1단계] 문서 검색 중...")
        
        retrieval_start_time = time.time()
        # BaseRetriever는 invoke 메서드를 통해 호출 (LangChain v2+)
        documents = self.retriever.invoke(question)
        retrieval_time = time.time() - retrieval_start_time
        
        if self.verbose:
            print(f"검색된 문서: {len(documents)}개 (소요 시간: {retrieval_time:.2f}초)")
            for i, doc in enumerate(documents, 1):
                url = doc.metadata.get("url") or doc.metadata.get("source", "")
                title = doc.metadata.get("title", "")
                print(f"  [{i}] {title or '제목 없음'} - {url or 'URL 없음'}")
        
        # 2. 답변 생성
        if self.verbose:
            print("\n[2단계] 답변 생성 중...")
        
        generation_start_time = time.time()
        answer = self.generator.generate(question=question, documents=documents)
        generation_time = time.time() - generation_start_time
        
        # 전체 소요 시간
        total_time = time.time() - total_start_time
        
        if self.verbose:
            print(f"\n[시간 측정]")
            print(f"  - 문서 검색: {retrieval_time:.2f}초")
            print(f"  - 답변 생성: {generation_time:.2f}초")
            print(f"  - 전체 소요: {total_time:.2f}초")
            print("\n" + "=" * 50)
            print("최종 답변")
            print("=" * 50)
            print(answer)
            print("=" * 50)
        
        result = {
            "answer": answer,
            "question": question,
            "timing": {
                "retrieval_time": round(retrieval_time, 3),
                "generation_time": round(generation_time, 3),
                "total_time": round(total_time, 3),
            },
        }
        
        if return_documents:
            result["documents"] = documents
        
        return result
    
    async def aquery(
        self,
        question: str,
        return_documents: bool = False,
    ) -> Dict[str, Any]:
        """비동기 버전의 질의."""
        if self.verbose:
            print("\n" + "=" * 50)
            print("RAG 파이프라인 실행 (비동기)")
            print("=" * 50)
        
        # 전체 시작 시간
        total_start_time = time.time()
        
        # 1. 문서 검색
        if self.verbose:
            print("\n[1단계] 문서 검색 중...")
        
        retrieval_start_time = time.time()
        # BaseRetriever는 ainvoke 메서드를 통해 호출 (LangChain v2+)
        documents = await self.retriever.ainvoke(question)
        retrieval_time = time.time() - retrieval_start_time
        
        if self.verbose:
            print(f"검색된 문서: {len(documents)}개 (소요 시간: {retrieval_time:.2f}초)")
        
        # 2. 답변 생성
        if self.verbose:
            print("\n[2단계] 답변 생성 중...")
        
        generation_start_time = time.time()
        answer = await self.generator.agenerate(question=question, documents=documents)
        generation_time = time.time() - generation_start_time
        
        # 전체 소요 시간
        total_time = time.time() - total_start_time
        
        if self.verbose:
            print(f"\n[시간 측정]")
            print(f"  - 문서 검색: {retrieval_time:.2f}초")
            print(f"  - 답변 생성: {generation_time:.2f}초")
            print(f"  - 전체 소요: {total_time:.2f}초")
            print("\n" + "=" * 50)
            print("최종 답변")
            print("=" * 50)
            print(answer)
            print("=" * 50)
        
        result = {
            "answer": answer,
            "question": question,
            "timing": {
                "retrieval_time": round(retrieval_time, 3),
                "generation_time": round(generation_time, 3),
                "total_time": round(total_time, 3),
            },
        }
        
        if return_documents:
            result["documents"] = documents
        
        return result


def get_rag_pipeline(
    persist_directory: str = "./chroma_db",
    k: int = 5,
    min_similarity_threshold: float = 0.3,
    llm_type: str = None,
    verbose: bool = True,
) -> RAGPipeline:
    """RAG 파이프라인 인스턴스를 생성하고 반환.
    
    Args:
        persist_directory: ChromaDB 저장 경로
        k: 검색할 문서 개수
        min_similarity_threshold: 최소 유사도 임계값
        llm_type: LLM 타입 ("huggingface" or "openai")
        verbose: 상세 출력 여부
        
    Returns:
        RAGPipeline 인스턴스
    """
    return RAGPipeline(
        persist_directory=persist_directory,
        k=k,
        min_similarity_threshold=min_similarity_threshold,
        llm_type=llm_type,
        verbose=verbose,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 질의 시스템")
    parser.add_argument(
        "question",
        type=str,
        help="질문",
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=5,
        help="검색할 문서 개수 (기본값: 5)",
    )
    parser.add_argument(
        "--llm-type",
        type=str,
        choices=["huggingface", "openai"],
        default=None,
        help="LLM 타입 (기본값: 환경 변수 또는 huggingface)",
    )
    parser.add_argument(
        "--no-verbose",
        action="store_true",
        help="상세 출력 비활성화",
    )
    args = parser.parse_args()
    
    # RAG 파이프라인 실행
    rag = get_rag_pipeline(
        k=args.top_k,
        llm_type=args.llm_type,
        verbose=not args.no_verbose,
    )
    
    result = rag.query(args.question, return_documents=True)

