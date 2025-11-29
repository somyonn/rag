#!/bin/bash
# 라즈베리파이4용 Docker 이미지 빌드 스크립트

set -e

echo "RAG 시스템 Docker 이미지 빌드 시작..."

# ARM64 플랫폼으로 빌드
docker build --platform linux/arm64 -t rag-system:latest .

echo "빌드 완료!"
echo ""
echo "이미지를 tar 파일로 저장하려면:"
echo "  docker save rag-system:latest | gzip > rag-system.tar.gz"
echo ""
echo "라즈베리파이에서 실행하려면:"
echo "  docker load < rag-system.tar.gz"
echo "  docker run --rm -v \$(pwd)/chroma_db:/app/chroma_db --env-file .env rag-system:latest python rag.py '질문'"


