#!/bin/bash
# Docker 컨테이너 실행 스크립트

set -e

# 질문이 제공되지 않으면 도움말 표시
if [ -z "$1" ]; then
    echo "사용법: $0 '질문 내용'"
    echo ""
    echo "예시:"
    echo "  $0 'AWS Lambda는 무엇인가요?'"
    exit 1
fi

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "[경고] .env 파일이 없습니다."
    echo "[경고] 환경 변수를 직접 설정하거나 .env 파일을 생성하세요."
fi

# Docker 컨테이너 실행
docker run --rm \
    -v "$(pwd)/chroma_db:/app/chroma_db" \
    -v "$(pwd)/urls.py:/app/urls.py" \
    --env-file .env \
    rag-system:latest \
    python rag.py "$1"


