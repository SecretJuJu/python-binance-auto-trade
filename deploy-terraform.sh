#!/bin/bash
set -e

echo "🚀 Deploying Bitcoin Trading Bot with Terraform..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# .env 파일이 있으면 로드
if [ -f .env ]; then
    echo -e "${BLUE}📄 Loading environment variables from .env file...${NC}"
    source .env
fi

# 환경 변수 확인 및 대화형 입력
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET" ]; then
    echo -e "${YELLOW}🔑 Binance API 키를 입력해주세요${NC}"
    read -p "Binance API Key: " BINANCE_API_KEY
    read -s -p "Binance Secret Key: " BINANCE_SECRET
    echo ""
    
    if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET" ]; then
        echo -e "${RED}❌ API 키와 Secret 키를 모두 입력해야 합니다.${NC}"
        exit 1
    fi
fi

# AWS 계정 및 리전 설정
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-ap-northeast-2}

echo -e "${BLUE}📋 배포 정보${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region: $AWS_REGION"
echo ""

# Terraform 변수 파일 생성 (API 키 제외)
echo -e "${YELLOW}📝 Creating terraform.tfvars...${NC}"
cat > terraform/terraform.tfvars << EOF
aws_region = "$AWS_REGION"
EOF

echo -e "${GREEN}✅ terraform.tfvars created${NC}"

# Terraform 초기화 및 배포
echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
cd terraform
terraform init

echo -e "${YELLOW}📋 Planning Terraform deployment...${NC}"
terraform plan

echo -e "${YELLOW}☁️ Applying Terraform configuration...${NC}"
terraform apply -auto-approve

# 출력값 가져오기
ECR_REPO_URL=$(terraform output -raw ecr_repository_url)
SNS_TOPIC_ARN=$(terraform output -raw sns_topic_arn)
ECS_CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)

echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"

# Secrets Manager에 Binance API 키 설정
echo -e "${YELLOW}🔐 Setting up Binance API credentials in Secrets Manager...${NC}"

# Get the secret ARN from Terraform output
SECRET_ARN=$(terraform output -raw secrets_manager_secret_arn)

# Create the secret value JSON
SECRET_JSON=$(cat <<EOF
{
  "api_key": "$BINANCE_API_KEY",
  "secret_key": "$BINANCE_SECRET"
}
EOF
)

# Update the secret
aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ARN" \
    --secret-string "$SECRET_JSON"

echo -e "${GREEN}✅ API credentials configured in Secrets Manager${NC}"

# Docker 이미지 빌드 및 푸시
echo -e "${YELLOW}🐳 Building and pushing Docker image...${NC}"
cd ..

# ECR 로그인
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URL

# Docker 이미지 빌드 (AMD64 플랫폼으로 ECS Fargate 호환)
docker build --platform linux/amd64 -t bitcoin-auto-trader .

# 태그 설정 및 푸시
docker tag bitcoin-auto-trader:latest $ECR_REPO_URL:latest
docker push $ECR_REPO_URL:latest

echo -e "${GREEN}✅ Docker image pushed successfully${NC}"

# 첫 번째 태스크 수동 실행 (테스트)
echo -e "${YELLOW}🧪 Running initial test task...${NC}"

# 기본 VPC의 첫 번째 공용 서브넷 가져오기
SUBNET_ID=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)" \
    --filters "Name=map-public-ip-on-launch,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text)

# 보안 그룹 ID 가져오기
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=bitcoin-auto-trader-ecs-tasks" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# 태스크 정의 ARN 가져오기
TASK_DEF_ARN=$(aws ecs list-task-definitions \
    --family-prefix bitcoin-auto-trader-task \
    --query 'taskDefinitionArns[0]' \
    --output text)

# 태스크 실행
TASK_ARN=$(aws ecs run-task \
    --cluster $ECS_CLUSTER_NAME \
    --task-definition $TASK_DEF_ARN \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],assignPublicIp=ENABLED,securityGroups=[$SECURITY_GROUP_ID]}" \
    --query 'tasks[0].taskArn' \
    --output text)

echo -e "${GREEN}✅ Test task started: $TASK_ARN${NC}"

echo ""
echo -e "${GREEN}🎉 배포가 완료되었습니다!${NC}"
echo ""
echo -e "${BLUE}📞 알림 설정:${NC}"
echo "  다음 명령어로 이메일 알림을 설정하세요:"
echo "  aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@example.com"
echo ""
echo -e "${BLUE}📊 모니터링:${NC}"
echo "  CloudWatch Logs: /ecs/bitcoin-auto-trader"
echo "  ECS 클러스터: $ECS_CLUSTER_NAME"
echo "  S3 버킷: $S3_BUCKET_NAME"
echo ""
echo -e "${BLUE}⏰ 스케줄:${NC}"
echo "  거래 봇이 10분마다 자동 실행됩니다"
echo ""
echo -e "${BLUE}🔧 관리 명령어:${NC}"
echo "  로그 확인: aws logs tail /ecs/bitcoin-auto-trader --follow"
echo "  태스크 수동 실행: aws ecs run-task --cluster $ECS_CLUSTER_NAME --task-definition $TASK_DEF_ARN --launch-type FARGATE"
echo "  스케줄 일시 중지: aws events disable-rule --name bitcoin-auto-trader-schedule"
echo "  스케줄 재개: aws events enable-rule --name bitcoin-auto-trader-schedule"
echo ""
echo -e "${YELLOW}⚠️ 주의사항:${NC}"
echo "  - 바이낸스 계정에 충분한 USDT를 입금해주세요"
echo "  - 첫 번째 실행 로그를 확인하여 정상 작동을 확인하세요"
echo "  - 필요시 config.json에서 거래 설정을 조정하세요" 