# 🔧 환경 설정 가이드

## 🔐 GitHub Secrets 설정 (필수)

### 1️⃣ GitHub Repository에서 Secrets 설정

Repository → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | 설명 | 예시 값 |
|-------------|------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM 사용자 액세스 키 | `AKIA1234567890EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM 사용자 시크릿 키 | `wJalrXUtnFEMI/K7MDENG/bPxRfiCY...` |
| `BINANCE_API_KEY` | 바이낸스 API 키 | `NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j` |
| `BINANCE_SECRET` | 바이낸스 시크릿 키 | `pHggrnlkfvMu2J8kegjXRbtdtXPi6uJFZvvnCorw...` |

### 2️⃣ AWS IAM 사용자 생성 방법

```bash
# 1. IAM 사용자 생성
aws iam create-user --user-name bitcoin-trader-github-actions

# 2. 정책 연결 (개발용 - 전체 권한)
aws iam attach-user-policy \
    --user-name bitcoin-trader-github-actions \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 3. 액세스 키 생성
aws iam create-access-key --user-name bitcoin-trader-github-actions
```

출력에서 `AccessKeyId`와 `SecretAccessKey`를 GitHub Secrets에 저장하세요.

### 3️⃣ 바이낸스 API 키 발급

1. [바이낸스 로그인](https://www.binance.com/ko) → 계정 관리 → API 관리
2. **Create API** 클릭
3. 설정:
   - Label: `Bitcoin Auto Trader`
   - **Enable Spot & Margin Trading**: ✅ 체크
   - **Enable Futures Trading**: ❌ 체크 해제
   - IP 제한: 비활성화 (AWS IP는 유동적)

## 💻 로컬 개발 환경 설정

### 1️⃣ .env 파일 생성 (로컬 테스트용)

```bash
# 환경 파일 복사
cp env.example .env
```

### 2️⃣ .env 파일 내용 수정

```bash
# ==============================================
# 🚀 비트코인 자동거래 봇 환경 설정 (로컬용)
# ==============================================

# 📊 거래소 API 설정 (필수)
BINANCE_API_KEY=your_actual_binance_api_key_here
BINANCE_SECRET=your_actual_binance_secret_key_here

# ☁️ AWS 설정 (로컬 테스트용)
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY...
AWS_DEFAULT_REGION=ap-northeast-2

# 💾 상태 저장 설정 (배포 후 값으로 변경)
S3_BUCKET=bitcoin-auto-trader-state-YOUR_ACCOUNT_ID-ap-northeast-2
DYNAMODB_TABLE=bitcoin-auto-trader-trading-state
USE_S3=true

# 📧 알림 설정 (배포 후 값으로 변경)
SNS_TOPIC_ARN=arn:aws:sns:ap-northeast-2:YOUR_ACCOUNT_ID:bitcoin-auto-trader-alerts
NOTIFY_ON_SUCCESS=false

# 🔧 기타 설정
LOG_LEVEL=INFO
TEST_MODE=true  # 로컬에서는 테스트 모드로!
```

## 🚀 배포 프로세스

### 자동 배포 (GitHub Actions)

1. **GitHub Secrets 설정** (위 참조)
2. **코드 푸시**:
   ```bash
   git add .
   git commit -m "Deploy trading bot"
   git push origin main
   ```
3. **배포 확인**: GitHub Actions 탭에서 진행 상황 확인

### 수동 배포 (로컬 Terraform)

```bash
# 1. AWS 인증 설정
aws configure

# 2. Terraform 변수 파일 생성
cd terraform
cat > terraform.tfvars << EOF
aws_region = "ap-northeast-2"
binance_api_key = "your_actual_api_key"
binance_secret = "your_actual_secret"
project_name = "bitcoin-auto-trader"
task_cpu = 512
task_memory = 1024
schedule_expression = "rate(10 minutes)"
notify_on_success = false
use_s3_instead_of_dynamodb = true
EOF

# 3. 배포 실행
terraform init
terraform plan
terraform apply
```

## 📋 설정 확인 체크리스트

### GitHub Secrets ✅
- [ ] `AWS_ACCESS_KEY_ID` 설정됨
- [ ] `AWS_SECRET_ACCESS_KEY` 설정됨  
- [ ] `BINANCE_API_KEY` 설정됨
- [ ] `BINANCE_SECRET` 설정됨

### AWS IAM 권한 ✅
- [ ] ECS 권한 (`ecs:*`)
- [ ] ECR 권한 (`ecr:*`)
- [ ] S3 권한 (`s3:*`)
- [ ] DynamoDB 권한 (`dynamodb:*`)
- [ ] IAM 권한 (`iam:*`)
- [ ] Secrets Manager 권한 (`secretsmanager:*`)
- [ ] SNS 권한 (`sns:*`)
- [ ] CloudWatch 권한 (`logs:*`)
- [ ] EventBridge 권한 (`events:*`)

### 바이낸스 API ✅
- [ ] 현물 거래 권한 활성화
- [ ] 선물 거래 권한 비활성화
- [ ] API 키 유효성 확인

## 🧪 테스트 방법

### 로컬 테스트

```bash
# 1. 설정 검증
poetry run python config_manager.py validate

# 2. API 연결 테스트
poetry run python -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_secret',
    'sandbox': False
})
print('Balance:', exchange.fetch_balance()['USDT'])
"

# 3. 백테스트 실행
poetry run python backtest.py --plot
```

### 배포 후 테스트

```bash
# 1. 로그 확인
aws logs tail /ecs/bitcoin-auto-trader --follow

# 2. 수동 실행
TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix bitcoin-auto-trader-task --query 'taskDefinitionArns[0]' --output text)
aws ecs run-task --cluster bitcoin-auto-trader-cluster --task-definition $TASK_DEF_ARN --launch-type FARGATE

# 3. SNS 구독
aws sns subscribe \
    --topic-arn $(terraform output -raw sns_topic_arn) \
    --protocol email \
    --notification-endpoint your-email@example.com
```

## ⚠️ 주의사항

1. **GitHub Secrets은 암호화됨** - 로그에 노출되지 않음
2. **로컬 .env는 .gitignore에 포함** - 커밋하지 말 것
3. **테스트 모드 활용** - 실제 거래 전 충분한 테스트
4. **API 키 권한 최소화** - 현물 거래만 활성화
5. **정기적인 키 교체** - 보안을 위해 6개월마다 교체 권장

## 🔍 트러블슈팅

### "Invalid API-key" 오류
```bash
# API 키 테스트
curl -H "X-MBX-APIKEY: your_api_key" 'https://api.binance.com/api/v3/account'
```

### "Access Denied" 오류
```bash
# AWS 권한 확인
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name bitcoin-trader-github-actions
```

### 배포 실패
1. GitHub Actions 로그 확인
2. AWS CloudWatch 로그 확인  
3. Terraform state 확인: `terraform state list` 