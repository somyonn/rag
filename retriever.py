"""RAG Retriever 구현.

기존 검색 로직을 LangChain의 Retriever 인터페이스로 래핑합니다.
"""

import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers.util import cos_sim

# 설정
PERSIST_DIRECTORY = "./chroma_db"

EMBEDDINGS_MODEL = HuggingFaceEmbeddings(
    model_name='jhgan/ko-sroberta-nli',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True},
)


def content_similarity(text1: str, text2: str) -> float:
    """두 텍스트의 내용 유사도를 계산 (간단한 Jaccard 유사도)"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0.0


class CustomChromaRetriever(BaseRetriever):
    """커스텀 ChromaDB Retriever.
    
    MMR 검색, 유사도 필터링, 중복 제거 등 고급 필터링을 제공합니다.
    """
    
    persist_directory: str
    k: int
    min_similarity_threshold: float
    content_similarity_threshold: float
    verbose: bool
    
    def __init__(
        self,
        persist_directory: str = PERSIST_DIRECTORY,
        k: int = 5,
        min_similarity_threshold: float = 0.3,
        content_similarity_threshold: float = 0.85,
        verbose: bool = False,
        **kwargs,
    ):
        """Retriever 초기화.
        
        Args:
            persist_directory: ChromaDB 저장 경로
            k: 반환할 문서 개수
            min_similarity_threshold: 최소 유사도 임계값
            content_similarity_threshold: 내용 유사도 임계값 (중복 제거용)
            verbose: 상세 출력 여부
            **kwargs: 추가 인자
        """
        # Vectorstore 초기화 (super 호출 전에 체크)
        if not os.path.exists(persist_directory):
            raise RuntimeError(
                f"Chroma DB가 존재하지 않습니다. 먼저 crawl_and_update.py를 실행하세요. ({persist_directory})"
            )
        
        # Pydantic 방식으로 필드 초기화
        super().__init__(
            persist_directory=persist_directory,
            k=k,
            min_similarity_threshold=min_similarity_threshold,
            content_similarity_threshold=content_similarity_threshold,
            verbose=verbose,
            **kwargs,
        )
        
        # Vectorstore는 인스턴스 변수로 저장
        # (Chroma 객체가 Pydantic 모델이 아니므로 필드로 선언하지 않음)
        self._vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=EMBEDDINGS_MODEL,
        )
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """쿼리에 관련된 문서를 검색.
        
        Args:
            query: 검색 쿼리
            
        Returns:
            관련 문서 리스트
        """
        if self.verbose:
            print(f"\n[Retriever] 쿼리: {query}")
        
        # MMR (Maximal Marginal Relevance) 방식으로 검색
        results = self._vectorstore.max_marginal_relevance_search(
            query,
            k=self.k * 5,  # 중복 제거 및 필터링을 위해 더 많이 가져옴
            fetch_k=self.k * 200,  # 후보 개수
            lambda_mult=0.2  # 관련성 우선 (0.2=관련성 강조)
        )
        
        # MMR은 점수를 직접 반환하지 않으므로, 결과에 대해 유사도 점수 계산
        query_embedding = EMBEDDINGS_MODEL.embed_query(query)
        results_with_scores = []
        
        for doc in results:
            doc_embedding = EMBEDDINGS_MODEL.embed_query(doc.page_content)
            score = cos_sim(doc_embedding, query_embedding).item()
            distance = 1 - score
            results_with_scores.append((doc, distance))
        
        # 1차 필터링: 최소 유사도 임계값 적용
        filtered_results = []
        for doc, distance in results_with_scores:
            similarity = 1 - distance
            if similarity >= self.min_similarity_threshold:
                filtered_results.append((doc, distance))
        
        # 임계값을 낮춰서 재검색 (결과가 없을 경우)
        if not filtered_results and self.verbose:
            print(f"[Retriever] 유사도 임계값({self.min_similarity_threshold}) 이상인 문서가 없습니다. 임계값을 낮춰 재검색합니다.")
            min_similarity_threshold = 0.1
            filtered_results = [
                (doc, dist) for doc, dist in results_with_scores
                if (1 - dist) >= min_similarity_threshold
            ]
        
        results_with_scores = filtered_results
        
        # 2차 필터링: 내용 유사도가 너무 높은 중복 문서 제거
        url_to_best_doc = {}
        seen_contents = {}
        
        for doc, score in results_with_scores:
            content_preview = doc.page_content.strip()[:300]
            content_hash = hash(content_preview)
            
            # 내용이 거의 동일한 문서 제거
            if content_hash in seen_contents:
                existing_doc, existing_score = seen_contents[content_hash]
                similarity = content_similarity(doc.page_content, existing_doc.page_content)
                if similarity > self.content_similarity_threshold:
                    if score < existing_score:
                        seen_contents[content_hash] = (doc, score)
                        existing_url = existing_doc.metadata.get("url") or existing_doc.metadata.get("source", "")
                        if existing_url and existing_url in url_to_best_doc:
                            if url_to_best_doc[existing_url][0] == existing_doc:
                                del url_to_best_doc[existing_url]
                    else:
                        continue
                else:
                    seen_contents[content_hash] = (doc, score)
            else:
                seen_contents[content_hash] = (doc, score)
            
            # URL 기준으로 중복 제거
            url = doc.metadata.get("url") or doc.metadata.get("source", "")
            if not url:
                key = f"{doc.metadata.get('title', '')}:{content_preview[:50]}"
                if key not in url_to_best_doc:
                    url_to_best_doc[key] = (doc, score)
                elif score < url_to_best_doc[key][1]:
                    url_to_best_doc[key] = (doc, score)
            else:
                if url not in url_to_best_doc:
                    url_to_best_doc[url] = (doc, score)
                elif score < url_to_best_doc[url][1]:
                    url_to_best_doc[url] = (doc, score)
        
        # 3차 reranking: 유사도 점수 순으로 정렬
        sorted_results = sorted(url_to_best_doc.values(), key=lambda x: x[1])
        
        # 상위 k개만 선택
        results_with_scores = sorted_results[:self.k]
        results = [doc for doc, _ in results_with_scores]
        
        if self.verbose:
            print(f"[Retriever] {len(results)}개 문서 검색 완료")
        
        return results
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """비동기 버전의 문서 검색 (동기 버전으로 구현)."""
        return self._get_relevant_documents(query)


def get_retriever(
    persist_directory: str = PERSIST_DIRECTORY,
    k: int = 5,
    min_similarity_threshold: float = 0.3,
    verbose: bool = False,
) -> CustomChromaRetriever:
    """Retriever 인스턴스를 생성하고 반환.
    
    Args:
        persist_directory: ChromaDB 저장 경로
        k: 반환할 문서 개수
        min_similarity_threshold: 최소 유사도 임계값
        verbose: 상세 출력 여부
        
    Returns:
        CustomChromaRetriever 인스턴스
    """
    return CustomChromaRetriever(
        persist_directory=persist_directory,
        k=k,
        min_similarity_threshold=min_similarity_threshold,
        verbose=verbose,
    )

