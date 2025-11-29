#!/bin/bash
# 라즈베리파이로 전송하는 스크립트

set -e

if [ -z "$1" ]; then
    echo "사용법: $0 pi@raspberrypi_ip"
    echo "예시: $0 pi@192.168.1.100"
    exit 1
fi

PI_HOST=$1
PI_USER=$(echo $PI_HOST | cut -d'@' -f1)
PI_IP=$(echo $PI_HOST | cut -d'@' -f2)

echo "라즈베리파이로 전송 중..."
echo "호스트: $PI_HOST"

# 1. 이미지를 tar 파일로 저장
echo "[1/3] Docker 이미지를 tar 파일로 저장 중..."
docker save rag-system:latest | gzip > rag-system.tar.gz

# 2. 필요한 파일들을 tar로 압축
echo "[2/3] 프로젝트 파일 압축 중..."
# 임시 디렉토리에 필요한 파일들만 복사
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 필요한 파일들 복사
cp *.py $TEMP_DIR/ 2>/dev/null || true
cp requirements.txt $TEMP_DIR/ 2>/dev/null || true
cp docker-compose.yml $TEMP_DIR/ 2>/dev/null || true
cp Dockerfile $TEMP_DIR/ 2>/dev/null || true
cp .dockerignore $TEMP_DIR/ 2>/dev/null || true
cp DOCKER_GUIDE.md $TEMP_DIR/ 2>/dev/null || true
cp build.sh $TEMP_DIR/ 2>/dev/null || true
cp run_docker.sh $TEMP_DIR/ 2>/dev/null || true
[ -f .env.example ] && cp .env.example $TEMP_DIR/ 2>/dev/null || true

# tar로 압축
cd $TEMP_DIR
tar -czf rag-files.tar.gz *
cd - > /dev/null
mv $TEMP_DIR/rag-files.tar.gz .

# 3. chroma_db 압축 (있는 경우)
chroma_db_included=true
if [ -d chroma_db ] && [ "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "[3/4] chroma_db 압축 중..."
    tar -czf chroma_db.tar.gz chroma_db/
    echo "  chroma_db 크기: $(du -sh chroma_db | cut -f1)"
else
    echo "[3/4] chroma_db가 없습니다. (건너뜀)"
    chroma_db_included=false
fi

# 4. 라즈베리파이로 전송
echo "[4/4] 라즈베리파이로 전송 중..."
FILES_TO_TRANSFER="rag-system.tar.gz rag-files.tar.gz"
if [ "$chroma_db_included" != "false" ]; then
    FILES_TO_TRANSFER="$FILES_TO_TRANSFER chroma_db.tar.gz"
fi
scp $FILES_TO_TRANSFER $PI_HOST:/home/$PI_USER/

# 5. 라즈베리파이에서 실행할 명령어 출력
echo ""
echo "전송 완료!"
echo ""
echo "라즈베리파이에서 다음 명령어를 실행하세요:"
echo ""
echo "  # 이미지 로드"
echo "  docker load < rag-system.tar.gz"
echo ""
echo "  # 파일 압축 해제"
echo "  tar -xzf rag-files.tar.gz"
echo ""
if [ "$chroma_db_included" != "false" ]; then
    echo "  # chroma_db 압축 해제 (별도 전송된 경우)"
    echo "  tar -xzf chroma_db.tar.gz"
    echo "  # 또는 이미지에 포함되어 있다면 볼륨 마운트 불필요"
    echo ""
fi
echo "  # .env 파일 생성 (필요한 경우)"
echo "  cat > .env << EOF"
echo "  LLM_TYPE=openai"
echo "  OPENAI_API_KEY=your_openai_api_key_here"
echo "  EOF"
echo "  nano .env  # API 키 등 설정"
echo ""
echo "  # 실행"
echo "  docker-compose up -d"
echo "  # 또는"
echo "  ./run_docker.sh '질문 내용'"

