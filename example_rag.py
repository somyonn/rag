"""RAG 시스템 사용 예제."""

from rag import get_rag_pipeline

# RAG 파이프라인 초기화
rag = get_rag_pipeline(
    k=5,  # 검색할 문서 개수
    min_similarity_threshold=0.3,  # 최소 유사도 임계값
    llm_type="huggingface",  # 또는 "openai"
    verbose=True,  # 상세 출력
)

# 질의 실행
question = "AWS Lambda는 무엇인가요?"

result = rag.query(question, return_documents=True)

print("\n" + "=" * 50)
print("최종 결과")
print("=" * 50)
print(f"질문: {result['question']}")
print(f"\n답변:\n{result['answer']}")
print(f"\n참고 문서 수: {len(result['documents'])}")

