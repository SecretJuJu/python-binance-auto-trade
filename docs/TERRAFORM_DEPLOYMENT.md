# 🚀 Terraform 배포 가이드

이 가이드는 Terraform을 사용하여 비트코인 자동거래 봇을 AWS ECS Fargate에 배포하는 방법을 설명합니다.

## 📋 개요

### 아키텍처

```
EventBridge (10분마다) 
    ↓
ECS Fargate Task (0개 유지, 필요시 실행)
    ↓
거래 로직 실행
    ↓
S3 상태 저장 + SNS 알림
    ↓
컨테이너 종료 (비용 최적화)
```

### 주요 구성 요소

- **ECS Fargate**: 서버리스 컨테이너 실행 환경
- **ECR**: Docker 이미지 저장소
- **EventBridge**: 10분마다 스케줄링
- **S3**: 거래 상태 저장
- **SNS**: 알림 시스템
- **Secrets Manager**: API 키 보안 저장
- **CloudWatch**: 로그 및 모니터링

## 🛠️ 사전 준비

### 1. 필수 도구 설치

```bash
# Terraform 설치 (macOS)
brew install terraform

# Docker 설치
brew install --cask docker

# AWS CLI 설치 및 설정
brew install awscli
aws configure
```

### 2. 환경 변수 설정

```bash
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_SECRET="your_binance_secret"
export AWS_REGION="ap-northeast-2"  # 선택사항
```

## 🚀 배포 방법

### 1. 자동 배포 (권장)

```bash
# 한 번의 명령으로 전체 배포
./deploy-terraform.sh
```

### 2. 수동 배포

```bash
# 1. Terraform 변수 파일 생성
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# terraform.tfvars 파일을 편집하여 실제 값 입력

# 2. Terraform 초기화
cd terraform
terraform init

# 3. 배포 계획 확인
terraform plan

# 4. 인프라 배포
terraform apply

# 5. Docker 이미지 빌드 및 푸시
cd ..
ECR_REPO_URL=$(cd terraform && terraform output -raw ecr_repository_url)

# ECR 로그인
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URL

# 이미지 빌드 및 푸시
docker build -t bitcoin-auto-trader .
docker tag bitcoin-auto-trader:latest $ECR_REPO_URL:latest
docker push $ECR_REPO_URL:latest
```

## ⚙️ 설정 사용자 정의

### Terraform 변수

`terraform/terraform.tfvars` 파일에서 다음 설정을 조정할 수 있습니다:

```hcl
# 스케줄 조정 (기본: 10분마다)
schedule_expression = "rate(5 minutes)"   # 5분마다
# schedule_expression = "cron(0 */1 * * ? *)"  # 1시간마다

# 리소스 조정
task_cpu    = 256   # 0.25 vCPU (더 저렴)
task_memory = 512   # 512 MB

# 성공 알림 활성화
notify_on_success = true
```

### 거래 설정

기존 `config.json`을 사용하여 거래 전략을 조정:

```bash
# 거래 설정 조정
npm run config -- set trade_amount 30
npm run config -- set sma_short 15
npm run config -- set sma_long 50

# 설정 확인
npm run config:show

# 백테스트
npm run backtest
```

## 📊 모니터링 및 관리

### 로그 확인

```bash
# 실시간 로그 확인
aws logs tail /ecs/bitcoin-auto-trader --follow

# 특정 기간 로그 확인
aws logs filter-log-events \
    --log-group-name "/ecs/bitcoin-auto-trader" \
    --start-time $(date -d '1 hour ago' +%s)000
```

### 수동 태스크 실행

```bash
# 환경 변수 설정
CLUSTER_NAME=$(cd terraform && terraform output -raw ecs_cluster_name)
TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix bitcoin-auto-trader-task --query 'taskDefinitionArns[0]' --output text)

# 기본 VPC 서브넷 및 보안 그룹 가져오기
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=map-public-ip-on-launch,Values=true" --query 'Subnets[0].SubnetId' --output text)
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=bitcoin-auto-trader-ecs-tasks" --query 'SecurityGroups[0].GroupId' --output text)

# 태스크 실행
aws ecs run-task \
    --cluster $CLUSTER_NAME \
    --task-definition $TASK_DEF_ARN \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],assignPublicIp=ENABLED,securityGroups=[$SECURITY_GROUP_ID]}"
```

### 스케줄 관리

```bash
# 스케줄 일시 중지
aws events disable-rule --name bitcoin-auto-trader-schedule

# 스케줄 재개
aws events enable-rule --name bitcoin-auto-trader-schedule

# 스케줄 상태 확인
aws events describe-rule --name bitcoin-auto-trader-schedule
```

### 알림 설정

```bash
# SNS 토픽 ARN 가져오기
SNS_TOPIC_ARN=$(cd terraform && terraform output -raw sns_topic_arn)

# 이메일 구독 추가
aws sns subscribe \
    --topic-arn $SNS_TOPIC_ARN \
    --protocol email \
    --notification-endpoint your-email@example.com

# 구독 목록 확인
aws sns list-subscriptions-by-topic --topic-arn $SNS_TOPIC_ARN
```

## 💰 비용 분석

### 예상 월 비용 (서울 리전 기준)

| 서비스 | 리소스 | 예상 비용 |
|--------|--------|-----------|
| ECS Fargate | 0.5 vCPU, 1GB RAM, 10분마다 1분 실행 | ~$2.50 |
| ECR | 1개 이미지 저장 | ~$0.10 |
| S3 | 상태 파일 저장 | ~$0.01 |
| SNS | 알림 전송 | ~$0.10 |
| CloudWatch | 로그 저장 | ~$0.50 |
| Secrets Manager | API 키 저장 | ~$0.40 |
| **총 예상 비용** | | **~$3.61/월** |

### 비용 최적화 팁

1. **리소스 조정**: CPU/메모리를 최소 요구사항에 맞춰 설정
2. **스케줄 조정**: 거래 빈도를 필요에 따라 조정
3. **로그 보존**: CloudWatch 로그 보존 기간 단축
4. **알림 최적화**: 성공 알림 비활성화

## 🔧 트러블슈팅

### 일반적인 문제

#### 1. Docker 이미지 푸시 실패

```bash
# ECR 로그인 재시도
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URL

# Docker 데몬 확인
docker info
```

#### 2. 태스크 실행 실패

```bash
# 태스크 상태 확인
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN

# 로그 확인
aws logs get-log-events \
    --log-group-name "/ecs/bitcoin-auto-trader" \
    --log-stream-name "ecs/bitcoin-trading-container/$TASK_ID"
```

#### 3. Secrets Manager 접근 오류

```bash
# 시크릿 확인
aws secretsmanager get-secret-value --secret-id bitcoin-auto-trader/binance

# 시크릿 수동 생성
aws secretsmanager create-secret \
    --name bitcoin-auto-trader/binance \
    --secret-string '{"api_key":"your_key","secret":"your_secret"}'
```

#### 4. 권한 오류

```bash
# IAM 역할 확인
aws iam get-role --role-name bitcoin-auto-trader-ecs-task-role

# 정책 연결 확인
aws iam list-attached-role-policies --role-name bitcoin-auto-trader-ecs-task-role
```

### 디버깅 도구

```bash
# 모든 ECS 태스크 상태 확인
aws ecs list-tasks --cluster $CLUSTER_NAME

# 태스크 정의 버전 확인
aws ecs describe-task-definition --task-definition bitcoin-auto-trader-task

# EventBridge 규칙 확인
aws events list-rules --name-prefix bitcoin-auto-trader

# S3 버킷 내용 확인
aws s3 ls s3://bitcoin-auto-trader-state-$AWS_ACCOUNT_ID-$AWS_REGION/
```

## 🗑️ 인프라 삭제

### 자동 삭제

```bash
./destroy.sh
```

### 수동 삭제

```bash
# Terraform으로 인프라 삭제
cd terraform
terraform destroy

# ECR 이미지 수동 삭제 (필요시)
aws ecr batch-delete-image \
    --repository-name bitcoin-auto-trader \
    --image-ids imageTag=latest

# S3 버킷 수동 삭제 (필요시)
aws s3 rm s3://bitcoin-auto-trader-state-$AWS_ACCOUNT_ID-$AWS_REGION --recursive
aws s3api delete-bucket --bucket bitcoin-auto-trader-state-$AWS_ACCOUNT_ID-$AWS_REGION
```

## 🔒 보안 모범 사례

1. **API 키 보안**: Secrets Manager 사용, 하드코딩 금지
2. **최소 권한**: IAM 정책 최소 권한 적용
3. **네트워크 보안**: 필요한 포트만 열기
4. **로그 암호화**: CloudWatch 로그 암호화 활성화
5. **정기 검토**: 권한 및 리소스 정기 검토

## 📈 고급 기능

### 멀티 환경 배포

```bash
# 개발 환경
terraform workspace new dev
terraform workspace select dev

# 프로덕션 환경
terraform workspace new prod
terraform workspace select prod
```

### 백업 자동화

```bash
# S3 버킷 백업 설정
aws s3api put-bucket-replication-configuration \
    --bucket bitcoin-auto-trader-state-$AWS_ACCOUNT_ID-$AWS_REGION \
    --replication-configuration file://backup-config.json
```

### 모니터링 알람

```bash
# CloudWatch 알람 생성
aws cloudwatch put-metric-alarm \
    --alarm-name "BitcoinTrader-TaskFailures" \
    --alarm-description "Alert when ECS tasks fail" \
    --metric-name TaskCount \
    --namespace AWS/ECS \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanThreshold
```

---

이제 Terraform으로 완전히 자동화된 비트코인 자동거래 봇을 배포할 수 있습니다! 
ECS Fargate의 서버리스 특성으로 실행 시에만 비용이 발생하여 매우 경제적입니다. 