# 🚀 배포 가이드

이 가이드는 비트코인 자동거래 봇을 AWS에 배포하는 전체 과정을 단계별로 설명합니다.

## 📋 사전 준비

### 1. 필수 계정 및 도구

- ✅ **AWS 계정** (신용카드 등록 필요)
- ✅ **바이낸스 계정** 및 API 키
- ✅ **GitHub 계정** (자동 배포용)
- ✅ **AWS CLI** 설치 및 설정
- ✅ **Git** 설치

### 2. 비용 예상

| 서비스 | 월 예상 비용 | 설명 |
|--------|-------------|------|
| AWS Lambda | ~$0.20 | 월 100만 호출 무료, 이후 호출당 과금 |
| Amazon S3 | ~$0.50 | 5GB 무료, 초과시 GB당 $0.023 |
| Amazon DynamoDB | ~$0.00 | 25GB 무료 |
| Amazon SNS | ~$0.50 | 이메일 전송 건당 $0.000075 |
| Amazon CloudWatch | ~$0.30 | 로그 저장 비용 |
| **총 예상 비용** | **~$1.50/월** | 소액 거래 기준 |

## 🔐 1단계: AWS IAM 설정

### GitHub Actions용 IAM 사용자 생성

```bash
# 1. IAM 사용자 생성
aws iam create-user --user-name bitcoin-trader-deployer

# 2. 관리자 권한 부여 (개발 단계)
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 3. 액세스 키 생성
aws iam create-access-key --user-name bitcoin-trader-deployer
```

**출력 예시:**
```json
{
    "AccessKey": {
        "UserName": "bitcoin-trader-deployer",
        "AccessKeyId": "AKIA...",
        "SecretAccessKey": "abcd...",
        "Status": "Active"
    }
}
```

⚠️ **중요**: `AccessKeyId`와 `SecretAccessKey`를 안전한 곳에 저장하세요!

### 프로덕션용 최소 권한 설정 (선택사항)

```bash
# 최소 권한 정책 생성
aws iam create-policy \
    --policy-name BitcoinTraderDeployPolicy \
    --policy-document file://docs/minimal-iam-policy.json

# 관리자 권한 제거
aws iam detach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 최소 권한 연결
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/BitcoinTraderDeployPolicy
```

## 💰 2단계: 바이낸스 API 키 발급

### API 키 생성

1. [바이낸스 로그인](https://www.binance.com/) 후 **계정 관리 → API 관리**
2. **Create API** 클릭
3. **Label**: `Bitcoin Auto Trader`
4. **Restrict access to trusted IPs only**: 비활성화 (Lambda IP는 유동적)
5. **Enable Spot & Margin Trading**: 활성화 ✅
6. **Enable Futures Trading**: 비활성화 ❌

### API 키 테스트

```bash
# 로컬에서 API 키 테스트
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET="your_secret_key"

# Python으로 테스트
python3 -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_secret_key',
    'sandbox': False
})
print('Balance:', exchange.fetch_balance()['USDT'])
print('BTC Price:', exchange.fetch_ticker('BTC/USDT')['last'])
"
```

## 🔄 3단계: GitHub Repository 설정

### Repository Fork/Clone

```bash
# 1. GitHub에서 fork 또는 새 repository 생성
git clone https://github.com/YOUR_USERNAME/python-binance-auto-trade.git
cd python-binance-auto-trade

# 2. 의존성 설치 (로컬 테스트용)
poetry install
npm install
```

### GitHub Secrets 설정

Repository Settings → Secrets and variables → Actions에서 다음 설정:

| Secret Name | Value | 설명 |
|-------------|-------|------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM 사용자 액세스 키 |
| `AWS_SECRET_ACCESS_KEY` | `abcd...` | IAM 사용자 시크릿 키 |
| `BINANCE_API_KEY` | `your_binance_api_key` | 바이낸스 API 키 |
| `BINANCE_SECRET` | `your_binance_secret` | 바이낸스 시크릿 키 |

## ⚙️ 4단계: 설정 조정

### 거래 설정 확인 및 수정

```bash
# 현재 설정 확인
npm run config:show

# 프리셋 목록 확인
npm run config:presets

# 보수적 설정 적용 (추천)
npm run config -- preset conservative

# 또는 수동 설정
npm run config -- set trade_amount 20
npm run config -- set sma_short 10
npm run config -- set sma_long 30
```

### 백테스트 실행

```bash
# 최근 4일간 백테스트
npm run backtest

# 차트 포함 백테스트
npm run backtest:chart

# 커스텀 기간 백테스트
poetry run python backtest.py --start 2024-11-01 --end 2024-12-01 --plot
```

## 🚀 5단계: 배포 실행

### 자동 배포 (GitHub Actions)

```bash
# master 브랜치에 push하면 자동 배포
git add .
git commit -m "Initial deployment"
git push origin master

# GitHub Actions 로그 확인
# https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

### 수동 배포 (선택사항)

```bash
# 환경변수 설정
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="abcd..."
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET="your_secret_key"

# 배포 실행
npm run deploy
```

## 📬 6단계: SNS 알림 설정

### 이메일 구독 추가

```bash
# 배포된 SNS 토픽 ARN 확인
SNS_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name bitcoin-auto-trader-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
    --output text)

echo "SNS Topic ARN: $SNS_TOPIC_ARN"

# 이메일 구독 추가
aws sns subscribe \
    --topic-arn $SNS_TOPIC_ARN \
    --protocol email \
    --notification-endpoint your-email@example.com
```

### 이메일 확인

1. 구독 확인 이메일이 도착합니다
2. **Confirm subscription** 링크 클릭
3. 구독 완료 확인

### 알림 테스트

```bash
# 알림 기능 테스트
export SNS_TOPIC_ARN=$SNS_TOPIC_ARN
npm run test:notifications
```

## 🔍 7단계: 배포 확인

### Lambda 함수 확인

```bash
# Lambda 함수 목록 확인
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `bitcoin-auto-trader`)].FunctionName'

# 함수 상세 정보
aws lambda get-function --function-name bitcoin-auto-trader-dev-autoTrade
```

### 수동 실행 테스트

```bash
# Lambda 함수 수동 실행
npm run invoke

# 실행 로그 확인
npm run logs
```

### CloudWatch 로그 확인

```bash
# 로그 그룹 확인
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/bitcoin-auto-trader"

# 최근 로그 확인
aws logs filter-log-events \
    --log-group-name "/aws/lambda/bitcoin-auto-trader-dev-autoTrade" \
    --start-time $(date -d '1 hour ago' +%s)000
```

## 📊 8단계: 모니터링 설정

### CloudWatch 대시보드 생성 (선택사항)

```bash
# 대시보드 생성을 위한 JSON 설정
cat > dashboard.json << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Invocations", "FunctionName", "bitcoin-auto-trader-dev-autoTrade"],
                    ["AWS/Lambda", "Errors", "FunctionName", "bitcoin-auto-trader-dev-autoTrade"],
                    ["AWS/Lambda", "Duration", "FunctionName", "bitcoin-auto-trader-dev-autoTrade"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "ap-northeast-2",
                "title": "Bitcoin Trading Bot Metrics"
            }
        }
    ]
}
EOF

# 대시보드 생성
aws cloudwatch put-dashboard \
    --dashboard-name "BitcoinTradingBot" \
    --dashboard-body file://dashboard.json
```

## 🚨 트러블슈팅

### 일반적인 문제들

1. **Secrets Manager 권한 오류** (ECS Fargate)
   ```
   ResourceInitializationError: unable to retrieve secret from asm: AccessDeniedException
   ```
   → `terraform/set-secrets.sh` 실행하여 Binance API 키 설정
   → 자세한 해결방법: `terraform/TROUBLESHOOTING.md` 참조

2. **ECS 컨테이너 이미지 없음**
   ```
   Unable to pull image: repository does not exist
   ```
   → ECR에 Docker 이미지 푸시 필요
   → `deploy-terraform.sh` 스크립트 사용 권장

3. **API 키 오류**
   ```
   {'code': -2015, 'msg': 'Invalid API-key, IP, or permissions for action'}
   ```
   → 바이낸스 API 키 재발급 및 권한 확인
   → Spot Trading 권한 활성화 필수

4. **잔고 부족**
   ```
   Insufficient USDT balance
   ```
   → 바이낸스 계정에 충분한 USDT 입금

### 로그 디버깅

```bash
# 실시간 로그 모니터링
aws logs tail /aws/lambda/bitcoin-auto-trader-dev-autoTrade --follow

# 오류 로그만 필터링
aws logs filter-log-events \
    --log-group-name "/aws/lambda/bitcoin-auto-trader-dev-autoTrade" \
    --filter-pattern "ERROR"
```

## 🔄 업데이트 및 유지보수

### 설정 변경

```bash
# 거래 금액 변경
npm run config -- set trade_amount 30

# 변경사항 배포
git add config.json
git commit -m "Update trade amount to 30 USDT"
git push origin master
```

### 정기 백테스트

```bash
# 월간 성과 분석
poetry run python backtest.py --start 2024-11-01 --end 2024-12-01 --plot

# 설정 최적화 후 백테스트
npm run config -- preset balanced
npm run backtest:chart
```

### 비용 모니터링

```bash
# 월간 AWS 비용 확인
aws ce get-cost-and-usage \
    --time-period Start=2024-11-01,End=2024-12-01 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

## 🛡️ 보안 체크리스트

- [ ] IAM 사용자에 MFA 설정
- [ ] 바이낸스 API 키에 IP 제한 설정 (필요시)
- [ ] GitHub Secrets 적절히 설정
- [ ] 불필요한 AWS 리소스 정기 정리
- [ ] 거래 로그 정기 확인
- [ ] API 키 정기 교체 (6개월마다)

---

**🎉 축하합니다! 비트코인 자동거래 봇이 성공적으로 배포되었습니다.**

이제 5분마다 자동으로 거래 전략이 실행되며, 중요한 이벤트는 이메일로 알림을 받게 됩니다. 