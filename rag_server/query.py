import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers.util import cos_sim
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
import chromadb
from config import (
    CHROMA_SERVER_HOST,
    CHROMA_SERVER_GRPC_PORT,
    CHROMA_SERVER_AUTH_TOKEN,
    CHROMA_COLLECTION_NAME,
    USE_SERVER_MODE,
    PERSIST_DIRECTORY,
)

EMBEDDINGS_MODEL = SentenceTransformerEmbeddings(
    model_name='jhgan/ko-sroberta-nli',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True},
)


def find_most_similar_document(query: str, k: int = 5, persist_directory: str = PERSIST_DIRECTORY):
    """Chroma DB에서 유사도 검색."""
    # 서버 모드 또는 로컬 모드 선택
    if USE_SERVER_MODE:
        # gRPC를 사용하여 ChromaDB 서버에 연결
        try:
            from chromadb import HttpClient
            
            # ChromaDB HttpClient 생성 (gRPC 지원)
            # 인증이 필요한 경우 Settings에 추가할 수 있습니다
            settings = chromadb.Settings(
                anonymized_telemetry=False,
            )
            
            # 인증 토큰이 설정되어 있으면 헤더에 추가
            if CHROMA_SERVER_AUTH_TOKEN and CHROMA_SERVER_AUTH_TOKEN != "":
                # HttpClient는 headers 파라미터를 지원하지 않으므로
                # Settings를 통해 인증 정보 전달 시도
                # 또는 환경 변수로 설정
                import os
                os.environ["CHROMA_SERVER_AUTH_TOKEN"] = CHROMA_SERVER_AUTH_TOKEN
            
            client = HttpClient(
                host=CHROMA_SERVER_HOST,
                port=8000,  # HTTP 포트 (내부적으로 gRPC 사용)
                settings=settings,
            )
            
            vectorstore = Chroma(
                client=client,
                collection_name=CHROMA_COLLECTION_NAME,
                embedding_function=EMBEDDINGS_MODEL,
            )
            print(f"[서버 모드] ChromaDB 서버에 연결됨: {CHROMA_SERVER_HOST}:8000 (HTTP/gRPC)")
        except Exception as e:
            print(f"[경고] 서버 연결 실패: {e}")
            print("[대체] 로컬 모드로 전환합니다.")
            # 로컬 모드로 폴백
            if not os.path.exists(persist_directory):
                raise RuntimeError(
                    f"Chroma DB가 존재하지 않습니다. 먼저 crawl_and_update.py를 실행하세요. ({persist_directory})"
                )
            vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=EMBEDDINGS_MODEL,
            )
    else:
        # 로컬 모드
        if not os.path.exists(persist_directory):
            raise RuntimeError(
                f"Chroma DB가 존재하지 않습니다. 먼저 crawl_and_update.py를 실행하세요. ({persist_directory})"
            )
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=EMBEDDINGS_MODEL,
        )

    # 데이터베이스에 데이터가 있는지 확인
    try:
        # 컬렉션 정보 확인
        if hasattr(vectorstore, '_collection'):
            collection = vectorstore._collection
            if hasattr(collection, 'count'):
                count = collection.count()
                print(f"[디버그] 데이터베이스에 {count}개의 문서가 있습니다.")
                if count == 0:
                    raise RuntimeError("데이터베이스가 비어있습니다. 먼저 crawl_and_update.py를 실행하여 데이터를 추가하세요.")
    except RuntimeError:
        raise  # RuntimeError는 다시 발생시킴
    except Exception as e:
        print(f"[디버그] 데이터베이스 확인 중 오류 (무시하고 계속): {e}")
    
    # MMR (Maximal Marginal Relevance) 방식으로 검색
    # 더 엄격한 설정으로 관련성 우선 검색
    # fetch_k: 후보 문서 개수 (더 많이 가져와서 다양성 고려)
    # lambda_mult: 다양성 가중치 (0~1, 낮을수록 관련성 우선)
    results = vectorstore.max_marginal_relevance_search(
        query, 
        k=k * 5,  # 필터링을 위해 더 많이 가져옴
        fetch_k=k * 20,  # 후보 개수
        lambda_mult=0.5  # 관련성 우선 (0=관련성만, 1=다양성만, 0.5=균형)
    )
    
    print(f"[디버그] MMR 검색 결과: {len(results)}개 문서 반환")
    
    if not results:
        print("[경고] 검색 결과가 없습니다. 데이터베이스에 관련 문서가 없거나 쿼리가 너무 구체적일 수 있습니다.")
        return []
    
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
    
    # 유사도 점수 출력 (디버깅)
    if results_with_scores:
        similarities = [1 - dist for _, dist in results_with_scores]
        print(f"[디버그] 유사도 점수 범위: 최소={min(similarities):.4f}, 최대={max(similarities):.4f}, 평균={sum(similarities)/len(similarities):.4f}")
    
    # 1차 필터링: 최소 유사도 임계값 적용 (너무 낮은 유사도 문서 제거)
    # 임계값을 점진적으로 낮춰가며 필터링
    min_similarity_thresholds = [0.3, 0.2, 0.1, 0.05, 0.0]  # 점진적으로 낮춤
    filtered_results = []
    
    for threshold in min_similarity_thresholds:
        filtered_results = [(doc, dist) for doc, dist in results_with_scores if (1 - dist) >= threshold]
        if filtered_results:
            if threshold < 0.3:
                print(f"[경고] 유사도 임계값을 {threshold:.2f}로 낮춰 {len(filtered_results)}개 문서를 찾았습니다.")
            break
    
    if not filtered_results:
        print("[경고] 모든 유사도 임계값에서 결과를 찾지 못했습니다. 필터링 없이 진행합니다.")
        filtered_results = results_with_scores
    
    print(f"[디버그] 1차 필터링 후: {len(filtered_results)}개 문서")
    results_with_scores = filtered_results
    
    # 유사도 점수 순으로 정렬 (점수가 낮을수록 더 유사)
    sorted_results = sorted(results_with_scores, key=lambda x: x[1])
    
    # 상위 k개만 선택
    results_with_scores = sorted_results[:k]
    results = [doc for doc, _ in results_with_scores]
    
    print(f"[디버그] 최종 결과: {len(results)}개 문서 반환")

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
        
        # 유사도 출력
        print(f"유사도: {similarity:.4f}")
        
        # 인덱스 정보 출력 (유사도와 내용 사이)
        if chunk_idx >= 0 and total_chunks > 0:
            print(f"[{chunk_idx}/{total_chunks - 1}]")
        else:
            print(f"[?/?]")
        
        print(f"내용: {doc.page_content}")
        print(f"메타데이터: {doc.metadata}")
        print("-" * 50)

    if len(results) < k:
        print(f"\n요청한 {k}개 중 {len(results)}개만 반환되었습니다.\n")

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