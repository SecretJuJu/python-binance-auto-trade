#!/bin/bash
set -e

echo "🗑️ Destroying Bitcoin Trading Bot infrastructure..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 확인 프롬프트
echo -e "${RED}⚠️ 경고: 모든 인프라가 삭제됩니다!${NC}"
echo "다음 리소스들이 삭제됩니다:"
echo "  - ECS 클러스터 및 태스크 정의"
echo "  - ECR 리포지토리 (Docker 이미지 포함)"
echo "  - S3 버킷 (거래 상태 데이터 포함)"
echo "  - SNS 토픽"
echo "  - CloudWatch 로그 그룹"
echo "  - Secrets Manager 시크릿"
echo "  - EventBridge 규칙"
echo "  - IAM 역할 및 정책"
echo ""

read -p "정말로 삭제하시겠습니까? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "삭제가 취소되었습니다."
    exit 0
fi

echo ""
echo -e "${YELLOW}🛑 스케줄 비활성화 중...${NC}"

# EventBridge 규칙 비활성화 (실행 중인 태스크 방지)
if aws events describe-rule --name bitcoin-auto-trader-schedule >/dev/null 2>&1; then
    aws events disable-rule --name bitcoin-auto-trader-schedule
    echo -e "${GREEN}✅ EventBridge 규칙이 비활성화되었습니다${NC}"
fi

echo -e "${YELLOW}🧹 S3 버킷 비우는 중...${NC}"

# S3 버킷 비우기 (버전 관리 포함)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-ap-northeast-2}
BUCKET_NAME="bitcoin-auto-trader-state-${AWS_ACCOUNT_ID}-${AWS_REGION}"

if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "  S3 버킷 ($BUCKET_NAME) 비우는 중..."
    
    # 모든 객체 버전 삭제
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --output json | \
    jq -r '.Versions[]? | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key version; do
        if [[ -n "$key" && -n "$version" ]]; then
            aws s3api delete-object --bucket "$BUCKET_NAME" --key "$key" --version-id "$version"
        fi
    done
    
    # 삭제 마커 제거
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --output json | \
    jq -r '.DeleteMarkers[]? | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key version; do
        if [[ -n "$key" && -n "$version" ]]; then
            aws s3api delete-object --bucket "$BUCKET_NAME" --key "$key" --version-id "$version"
        fi
    done
    
    echo -e "${GREEN}✅ S3 버킷이 비워졌습니다${NC}"
else
    echo "  S3 버킷을 찾을 수 없습니다. 건너뜁니다."
fi

echo -e "${YELLOW}🐳 ECR 이미지 삭제 중...${NC}"

# ECR 이미지 삭제
if aws ecr describe-repositories --repository-names bitcoin-auto-trader >/dev/null 2>&1; then
    echo "  ECR 이미지 삭제 중..."
    aws ecr batch-delete-image \
        --repository-name bitcoin-auto-trader \
        --image-ids imageTag=latest 2>/dev/null || true
    echo -e "${GREEN}✅ ECR 이미지가 삭제되었습니다${NC}"
else
    echo "  ECR 리포지토리를 찾을 수 없습니다. 건너뜁니다."
fi

echo -e "${YELLOW}🏗️ Terraform으로 인프라 삭제 중...${NC}"

# Terraform destroy 실행
cd terraform

if [ -f "terraform.tfstate" ]; then
    terraform destroy -auto-approve
    echo -e "${GREEN}✅ Terraform 인프라가 삭제되었습니다${NC}"
else
    echo -e "${YELLOW}⚠️ terraform.tfstate 파일을 찾을 수 없습니다. 수동 정리가 필요할 수 있습니다.${NC}"
fi

cd ..

echo ""
echo -e "${GREEN}🎉 인프라 삭제가 완료되었습니다!${NC}"
echo ""
echo -e "${BLUE}🧹 정리 완료 항목:${NC}"
echo "  ✅ ECS 클러스터 및 태스크"
echo "  ✅ ECR 리포지토리 및 이미지"
echo "  ✅ S3 버킷 및 데이터"
echo "  ✅ SNS 토픽"
echo "  ✅ CloudWatch 로그"
echo "  ✅ Secrets Manager 시크릿"
echo "  ✅ EventBridge 규칙"
echo "  ✅ IAM 역할 및 정책"
echo ""
echo -e "${YELLOW}📝 참고사항:${NC}"
echo "  - terraform.tfstate 파일은 삭제되지 않았습니다"
echo "  - 수동으로 생성한 리소스가 있다면 별도로 삭제해주세요"
echo "  - 비용 발생이 완전히 중단되었는지 AWS 콘솔에서 확인하세요" 