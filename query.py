import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers.util import cos_sim
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 설정
PERSIST_DIRECTORY = "./chroma_db"

EMBEDDINGS_MODEL = HuggingFaceEmbeddings(
    model_name='jhgan/ko-sroberta-nli',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True},
)


def find_most_similar_document(query: str, k: int = 5, persist_directory: str = PERSIST_DIRECTORY):
    """Chroma DB에서 유사도 검색."""
    # 로컬 모드
    if not os.path.exists(persist_directory):
        raise RuntimeError(
            f"Chroma DB가 존재하지 않습니다. 먼저 crawl_and_update.py를 실행하세요. ({persist_directory})"
        )

    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=EMBEDDINGS_MODEL,
    )

    # MMR (Maximal Marginal Relevance) 방식으로 검색
    # 더 엄격한 설정으로 관련성 우선 검색
    # fetch_k: 후보 문서 개수 (더 많이 가져와서 다양성 고려)
    # lambda_mult: 다양성 가중치 (0~1, 낮을수록 관련성 우선)
    # 0.2로 설정하여 관련성을 더 강조 (기존 0.5보다 엄격)
    results = vectorstore.max_marginal_relevance_search(
        query, 
        k=k * 5,  # 중복 제거 및 필터링을 위해 더 많이 가져옴 (기존 k*2에서 증가)
        fetch_k=k * 200,  # 후보 개수 증가 (기존 k*100에서 증가)
        lambda_mult=0.2  # 관련성 우선 (0=관련성만, 1=다양성만, 0.2=관련성 강조)
    )
    
    # MMR은 점수를 직접 반환하지 않으므로, 결과에 대해 유사도 점수 계산
    query_embedding = EMBEDDINGS_MODEL.embed_query(query)
    results_with_scores = []
    
    for doc in results:
        doc_embedding = EMBEDDINGS_MODEL.embed_query(doc.page_content)
        # cosine similarity 계산
        score = cos_sim(doc_embedding, query_embedding).item()
        # 거리로 변환 (MMR은 거리 기반이므로)
        distance = 1 - score
        results_with_scores.append((doc, distance))
    
    # 1차 필터링: 최소 유사도 임계값 적용 (너무 낮은 유사도 문서 제거)
    min_similarity_threshold = 0.3  # 최소 유사도 0.3 이상만 통과
    filtered_results = []
    for doc, distance in results_with_scores:
        similarity = 1 - distance  # 거리를 유사도로 변환
        if similarity >= min_similarity_threshold:
            filtered_results.append((doc, distance))
    
    if not filtered_results:
        print(f"[경고] 유사도 임계값({min_similarity_threshold}) 이상인 문서가 없습니다. 임계값을 낮춰 재검색합니다.")
        # 임계값을 낮춰서 재검색
        min_similarity_threshold = 0.1
        filtered_results = [(doc, dist) for doc, dist in results_with_scores if (1 - dist) >= min_similarity_threshold]
    
    results_with_scores = filtered_results
    
    # 2차 필터링: 내용 유사도가 너무 높은 중복 문서 제거
    # 같은 내용이나 거의 비슷한 내용의 문서는 하나만 유지
    def content_similarity(text1: str, text2: str) -> float:
        """두 텍스트의 내용 유사도를 계산 (간단한 Jaccard 유사도)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    # 2차 필터링: URL 기준으로 중복 제거 및 내용 중복 제거
    # 같은 URL에서 가장 유사도 높은 청크 하나만 선택
    url_to_best_doc = {}
    seen_contents = {}  # 내용 해시 -> (doc, score) 매핑
    
    for doc, score in results_with_scores:
        # 내용의 앞부분으로 해시 생성 (중복 감지용)
        content_preview = doc.page_content.strip()[:300]  # 앞 300자
        content_hash = hash(content_preview)
        
        # 내용이 거의 동일한 문서 제거 (내용 유사도 0.85 이상)
        if content_hash in seen_contents:
            existing_doc, existing_score = seen_contents[content_hash]
            similarity = content_similarity(doc.page_content, existing_doc.page_content)
            if similarity > 0.85:  # 85% 이상 유사하면 중복으로 간주
                # 더 유사도 높은 문서만 유지
                if score < existing_score:  # 거리가 작을수록 더 유사
                    seen_contents[content_hash] = (doc, score)
                    # 기존 문서를 url_to_best_doc에서도 제거하고 새 문서로 교체
                    existing_url = existing_doc.metadata.get("url") or existing_doc.metadata.get("source", "")
                    if existing_url and existing_url in url_to_best_doc:
                        if url_to_best_doc[existing_url][0] == existing_doc:
                            del url_to_best_doc[existing_url]
                else:
                    continue  # 기존 문서가 더 좋으므로 현재 문서 스킵
            else:
                # 유사도가 낮으면 다른 문서로 간주
                seen_contents[content_hash] = (doc, score)
        else:
            seen_contents[content_hash] = (doc, score)
        
        url = doc.metadata.get("url") or doc.metadata.get("source", "")
        if not url:
            # URL이 없으면 제목과 내용으로 구분
            key = f"{doc.metadata.get('title', '')}:{content_preview[:50]}"
            if key not in url_to_best_doc:
                url_to_best_doc[key] = (doc, score)
            elif score < url_to_best_doc[key][1]:  # 점수가 낮을수록 더 유사 (거리)
                url_to_best_doc[key] = (doc, score)
        else:
            # 같은 URL이면 더 유사도 높은 것만 유지
            if url not in url_to_best_doc:
                url_to_best_doc[url] = (doc, score)
            elif score < url_to_best_doc[url][1]:  # 점수가 낮을수록 더 유사 (거리)
                url_to_best_doc[url] = (doc, score)

    # 3차 reranking: 유사도 점수 순으로 정렬 (점수가 낮을수록 더 유사)
    sorted_results = sorted(url_to_best_doc.values(), key=lambda x: x[1])
    
    # 상위 k개만 선택
    results_with_scores = sorted_results[:k]
    results = [doc for doc, _ in results_with_scores]

    # 각 문서의 청크 인덱스 정보 수집
    url_to_chunks = {}  # URL별로 모든 청크를 저장
    for doc, _ in results_with_scores:
        url = doc.metadata.get("url") or doc.metadata.get("source", "")
        if url and url not in url_to_chunks:
            # 해당 URL의 모든 문서 가져오기 (큰 k 값으로 검색)
            try:
                # 해당 URL의 문서들을 모두 가져오기 위해 넓은 범위로 검색
                all_docs_for_url = vectorstore.similarity_search(
                    doc.page_content[:50], k=1000  # 충분히 큰 값
                )
                # URL이 일치하는 문서만 필터링
                filtered = [
                    d.page_content for d in all_docs_for_url
                    if (d.metadata.get("url") == url or d.metadata.get("source") == url)
                ]
                url_to_chunks[url] = filtered
            except Exception as e:
                url_to_chunks[url] = []

    print("\n" + "=" * 50)
    print("Chroma DB에서 유사도 검색 결과:")
    for doc, score in results_with_scores:
        # 유사도 점수를 유사도 값으로 변환
        similarity = 1 / (1 + score)  # 거리를 유사도로 변환 (0~1 범위)
        
        # 해당 문서에서의 청크 인덱스 찾기
        url = doc.metadata.get("url") or doc.metadata.get("source", "")
        chunk_idx = -1
        total_chunks = 0
        
        if url and url in url_to_chunks:
            chunks = url_to_chunks[url]
            total_chunks = len(chunks)
            # 현재 청크의 내용과 일치하는 인덱스 찾기
            for i, chunk_content in enumerate(chunks):
                if isinstance(chunk_content, str):
                    if chunk_content.strip() == doc.page_content.strip() or \
                       chunk_content[:100] == doc.page_content[:100]:
                        chunk_idx = i
                        break
                elif hasattr(chunk_content, 'page_content'):
                    if chunk_content.page_content.strip() == doc.page_content.strip():
                        chunk_idx = i
                        break
        
        # 인덱스 정보 출력
        if chunk_idx >= 0 and total_chunks > 0:
            print(f"[{chunk_idx}/{total_chunks - 1}] 유사도: {similarity:.4f}")
        else:
            print(f"[?/?] 유사도: {similarity:.4f}")
        
        print(f"내용: {doc.page_content}")
        print(f"메타데이터: {doc.metadata}")
        print("-" * 50)

    if len(results) < k:
        print(f"\n요청한 {k}개 중 {len(results)}개만 반환되었습니다. 중복 문서를 제외했습니다.\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 질의 시스템")
    parser.add_argument(
        "query",
        type=str,
        help="검색할 질의",
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        default=5,
        help="반환할 상위 문서 개수 (기본값: 5)",
    )
    args = parser.parse_args()

    # 유사도 검색
    find_most_similar_document(args.query, k=args.top_k)