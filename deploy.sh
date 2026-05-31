#!/bin/bash

# ========================================================== #
# TONES_Server GCP Cloud Run 원클릭 배포 자동화 스크립트         #
# 설명: 로컬 gcloud CLI 인증 정보를 활용하여 백엔드 컨테이너를   #
#       GCP us-central1 리전에 CPU 1, RAM 2GB로 배포합니다.    #
# ========================================================== #

# 1. 인프라 설정 상수 선언 (사용자 설정에 맞추어 커스텀 변경 가능)
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
SERVICE_NAME="tones-server"
REPO_NAME="tones-repo"
IMAGE_NAME="tones-server"

# 프로젝트 ID 검증
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "❌ [Error] gcloud 프로젝트 ID가 설정되지 않았습니다."
    echo "💡 'gcloud config set project [YOUR_PROJECT_ID]' 명령어로 프로젝트를 설정한 후 재시도하세요."
    exit 1
fi

echo "=========================================================="
echo "🚀 TONES 백엔드 서비스 GCP Cloud Run 배포를 시작합니다."
echo "   - GCP 프로젝트: $PROJECT_ID"
echo "   - 대상 리전  : $REGION"
echo "   - 서비스 이름: $SERVICE_NAME"
echo "=========================================================="

# 2. GCP Artifact Registry 레포지토리 자동 생성 (미존재 시)
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

# 3. Cloud Build를 사용한 빌드 및 배포 기동
echo "🏗️ 2. Google Cloud Build를 활용하여 원격 컨테이너 빌드 시작..."
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "=========================================================="
    echo "🎉 백엔드 배포 파이프라인 기동 성공!"
    echo "   - GCP 콘솔 'Cloud Run' 메뉴 또는 'Cloud Build' 메뉴에서"
    echo "     진행 중인 무중단 롤링 배포 상세 현황을 모니터링할 수 있습니다."
    echo "=========================================================="
else
    echo "❌ [Error] 빌드 파이프라인 기동 실패. 로그를 확인하세요."
    exit 1
fi
