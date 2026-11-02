"""
ChromaDB 서버 설정
"""
import os

# ChromaDB 서버 설정
CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "localhost")
CHROMA_SERVER_HTTP_PORT = int(os.getenv("CHROMA_SERVER_HTTP_PORT", "8000"))
CHROMA_SERVER_GRPC_PORT = int(os.getenv("CHROMA_SERVER_GRPC_PORT", "50051"))
# 인증 토큰 (비어있으면 인증 없이 연결)
CHROMA_SERVER_AUTH_TOKEN = os.getenv("CHROMA_SERVER_AUTH_TOKEN", "")

# ChromaDB 컬렉션 이름
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_documents")

# 서버 모드 사용 여부 (환경 변수로 제어 가능)
USE_SERVER_MODE = os.getenv("USE_SERVER_MODE", "true").lower() == "true"

# 로컬 모드용 (서버 모드가 아닐 때)
PERSIST_DIRECTORY = "./chroma_db"
