#!/bin/bash

# ========================================================== #
# TONES_Server GCP Cloud Run 원클릭 배포 자동화 스크립트         #
# 설명: .env의 환경변수를 읽어 Cloud Build 치환 변수로 넘기고,   #
#       GCP us-central1 리전에 CPU 1, RAM 2GB로 배포합니다.    #
# ========================================================== #

# 1. 인프라 설정 상수 선언
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
SERVICE_NAME="tones-server"
REPO_NAME="tones-repo"

# 2. .env에서 배포에 필요한 환경변수 읽기
if [ -f .env ]; then
    CLOUD_SQL_INSTANCE=$(grep '^CLOUD_SQL_CONNECTION_NAME=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DB_USER=$(grep         '^DB_USER='                    .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DB_PASS=$(grep         '^DB_PASS='                    .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DB_NAME=$(grep         '^DB_NAME='                    .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    DB_HOST=$(grep         '^DB_HOST='                    .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    GEMINI_API_KEY=$(grep  '^GEMINI_API_KEY='             .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    SECRET_KEY=$(grep      '^SECRET_KEY='                 .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
else
    echo "⚠️  [Warning] .env 파일이 없습니다. .env.example을 복사한 후 값을 채워주세요."
    echo "   cp .env.example .env"
    exit 1
fi

# 3. 필수 변수 검증
MISSING=""
[ -z "$CLOUD_SQL_INSTANCE" ] && MISSING="$MISSING CLOUD_SQL_CONNECTION_NAME"
[ -z "$DB_USER"            ] && MISSING="$MISSING DB_USER"
[ -z "$DB_PASS"            ] && MISSING="$MISSING DB_PASS"
[ -z "$DB_NAME"            ] && MISSING="$MISSING DB_NAME"
[ -z "$GEMINI_API_KEY"     ] && MISSING="$MISSING GEMINI_API_KEY"
[ -z "$SECRET_KEY"         ] && MISSING="$MISSING SECRET_KEY"

if [ -n "$MISSING" ]; then
    echo "❌ [Error] .env에 다음 필수 변수가 설정되지 않았습니다:$MISSING"
    exit 1
fi

# 4. GCP 프로젝트 ID 검증
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "❌ [Error] gcloud 프로젝트 ID가 설정되지 않았습니다."
    echo "💡 'gcloud config set project [YOUR_PROJECT_ID]' 명령어로 설정 후 재시도하세요."
    exit 1
fi

echo "=========================================================="
echo "🚀 TONES 백엔드 서비스 GCP Cloud Run 배포를 시작합니다."
echo "   - GCP 프로젝트  : $PROJECT_ID"
echo "   - 대상 리전    : $REGION"
echo "   - 서비스 이름  : $SERVICE_NAME"
echo "   - Cloud SQL   : $CLOUD_SQL_INSTANCE"
echo "=========================================================="

# 5. GCP Artifact Registry 레포지토리 자동 생성 (미존재 시)
echo "📦 1. Artifact Registry 레포지토리 구성 확인 중..."
gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "   ➡️ 레포지토리가 존재하지 않아 신규 생성합니다: $REPO_NAME"
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="TONES Docker Container Repository" \
        --project=$PROJECT_ID
else
    echo "   ✅ 레포지토리 준비 완료: $REPO_NAME"
fi

# 6. Cloud Build를 사용한 빌드 및 배포
#    - .env는 .gitignore에 포함되어 빌드 컨텍스트에서 제외됨
#    - 따라서 앱 구동에 필요한 모든 env var을 --set-env-vars로 Cloud Run에 직접 주입
echo "🏗️ 2. Google Cloud Build를 활용하여 원격 컨테이너 빌드 시작..."
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=\
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest"),\
_CLOUD_SQL_INSTANCE="$CLOUD_SQL_INSTANCE",\
_DB_USER="$DB_USER",\
_DB_PASS="$DB_PASS",\
_DB_NAME="$DB_NAME",\
_DB_HOST="${DB_HOST:-localhost}",\
_GEMINI_API_KEY="$GEMINI_API_KEY",\
_SECRET_KEY="$SECRET_KEY" \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "=========================================================="
    echo "🎉 백엔드 배포 파이프라인 기동 성공!"
    echo "   - GCP 콘솔 'Cloud Run' 또는 'Cloud Build' 메뉴에서"
    echo "     진행 중인 무중단 롤링 배포 현황을 모니터링할 수 있습니다."
    echo "=========================================================="
else
    echo "❌ [Error] 빌드 파이프라인 기동 실패. 로그를 확인하세요."
    exit 1
fi
