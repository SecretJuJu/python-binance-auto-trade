# 🧠 AI 기반 비트코인 자동매매 시스템

이 프로젝트는 단순 이동평균 교차(SMA Crossover) 전략을 기반으로  
BTC/USDT 마켓에서 자동으로 매수/매도 거래를 수행하는 서버리스 트레이딩 봇입니다.

- 실거래는 **AWS Lambda** 상에서 자동 실행되며
- 전략 검증은 로컬에서 **백테스트**를 통해 가능합니다.

---

## ✅ 주요 특징

- **SMA(5) > SMA(20)** 시 매수, 반대일 경우 수익 조건에 따라 매도
- **바이낸스(Binance) 실거래 연동** (ccxt 사용)
- **5분 간격 자동 실행** - AWS EventBridge 스케줄링
- **초기 자산 100 USDT**, 거래당 90 USDT 투자 (공격적 설정)
- **수수료(0.2%) 포함 수익 조건 만족 시에만 매도**
- **최근 거래 상태(S3 또는 DynamoDB)에 저장 및 복원**
- **AWS Serverless Framework**로 인프라 구성
- **Python 3.11 + Poetry** 환경
- **로컬 백테스트 CLI 지원**

---

## 📁 프로젝트 구조

```
python-binance-auto-trade/
├── lambda_handler.py      # Lambda 메인 핸들러
├── trade.py              # 바이낸스 실거래 로직
├── state_store.py        # 거래 상태 저장/조회 (S3/DynamoDB)
├── backtest.py           # 로컬 백테스트 CLI
├── config.json           # 거래 설정 파일 (SMA, 거래금액 등)
├── config_loader.py      # 설정 파일 로더
├── config_manager.py     # 설정 관리 CLI 도구
├── serverless.yml        # Serverless Framework 설정
├── pyproject.toml        # Poetry 의존성 관리
├── requirements.txt      # Lambda용 의존성
├── package.json          # Serverless 플러그인 관리
├── env.example           # 환경 변수 예시
└── README.md
```

---

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
# Poetry 설치 (미설치 시)
curl -sSL https://install.python-poetry.org | python3 -

# 프로젝트 의존성 설치
poetry install

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. Node.js 의존성 설치 (Serverless Framework)

```bash
npm install
```

### 3. 코드 품질 도구 사용

```bash
# 코드 포맷팅 (Black + isort)
npm run format

# 린트 검사 (flake8)
npm run lint

# 전체 검사
npm run check
```

### 4. 설정 관리

```bash
# 현재 거래 설정 보기
npm run config:show

# 사용 가능한 프리셋 보기
npm run config:presets

# 보수적 설정 적용 (안전한 거래)
npm run config -- preset conservative

# 균형잡힌 설정 적용 (권장)
npm run config -- preset balanced

# 공격적 설정 적용 (위험도 높음)
npm run config -- preset aggressive

# 개별 설정 변경
npm run config -- set trade_amount 30
npm run config -- set sma_short 5

# 설정 유효성 검사
npm run config:validate
```

### 5. 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집하여 API 키 입력
# BINANCE_API_KEY=your_actual_api_key
# BINANCE_SECRET=your_actual_secret_key
# (SNS 토픽은 배포시 자동 생성됩니다)
```

### 6. 바이낸스 API 키 발급

1. [바이낸스 계정](https://www.binance.com/) 생성 및 로그인
2. **계정 관리 > API 관리**에서 새 API 키 생성
3. **현물 거래** 권한 활성화
4. API 키와 시크릿 키를 `.env` 파일에 입력

---

## 💰 거래 전략

### SMA Crossover 전략 (최적화)
- **매수 조건**: SMA(7) > SMA(25) 골든 크로스
- **매도 조건**: SMA(7) < SMA(25) + 수익률 0.3% 이상
- **거래 간격**: 5분 단위 캔들 기준
- **거래 단위**: 90 USDT씩 고정 (공격적 설정)
- **포지션**: 최대 1개 (추가 매수 금지)
- **수수료**: 매수/매도 각각 0.1% (총 0.2%)

---

## 🔄 백테스트 실행

로컬에서 전략 성과를 시뮬레이션할 수 있습니다.

### 빠른 실행 (npm scripts)
```bash
npm run backtest
```

### 커스텀 날짜 범위
```bash
# 직접 날짜 지정
python backtest.py --start 2024-05-01 --end 2024-05-30

# 차트 포함
python backtest.py --start 2024-05-01 --end 2024-05-30 --plot

# Poetry 사용 시
poetry run python backtest.py --start 2024-05-01 --end 2024-05-30
```

### 백테스트 결과 예시
```
============================================================
백테스트 결과
============================================================
초기 자산: $100.00
최종 자산: $108.45
총 수익률: 8.45%
Buy & Hold 수익률: 12.30%
전략 초과 수익률: -3.85%

총 거래 횟수: 5
승률: 80.0% (4/5)
총 수익: $8.45
거래당 평균 수익: $1.69
최대 손실: -2.15%
```

---

## 📬 SNS 알림 설정

SNS 토픽은 배포 시 자동으로 생성되며, 이메일 구독만 설정하면 됩니다.

### 1. 배포 후 이메일 구독 추가

```bash
# 배포 후 토픽 ARN 확인
aws cloudformation describe-stacks \
  --stack-name bitcoin-auto-trader-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
  --output text

# 이메일 구독 추가 (토픽 ARN 사용)
aws sns subscribe \
  --topic-arn <위에서_확인한_토픽_ARN> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

또는 AWS Console에서:
1. SNS → Topics → `bitcoin-auto-trader-dev-alerts` 선택
2. "Create subscription" 클릭
3. Protocol: Email, Endpoint: 본인 이메일 입력
4. 이메일 확인 후 구독 승인

### 2. 알림 기능

- 🎉 **수익 실현**: 매도 주문으로 수익을 달성했을 때
- 💰 **거래 실행**: 매수/매도 주문이 체결되었을 때  
- ⚠️ **잔고 부족**: 매수에 필요한 자금이 부족할 때
- ❌ **오류 발생**: API 오류, 네트워크 오류 등 문제 상황
- 🚀 **봇 시작**: Lambda 함수가 시작될 때 (선택사항)

### 3. 알림 테스트

```bash
# 배포 후 알림 기능 테스트
export SNS_TOPIC_ARN=$(aws cloudformation describe-stacks --stack-name bitcoin-auto-trader-dev --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' --output text)
npm run test:notifications
```

---

## 🔐 AWS IAM 권한 설정

배포를 위해 적절한 AWS IAM 권한이 필요합니다. 개발/테스트 단계에서는 관리자 권한을, 프로덕션에서는 최소 권한을 권장합니다.

### 1. GitHub Actions용 IAM 사용자 생성

#### 관리자 권한 설정 (개발/테스트용)

```bash
# IAM 사용자 생성
aws iam create-user --user-name bitcoin-trader-deployer

# 관리자 권한 부여 (개발 단계 권장)
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 액세스 키 생성 및 저장
aws iam create-access-key --user-name bitcoin-trader-deployer
```

#### 최소 권한 설정 (프로덕션용)

배포를 위해 최소한으로 필요한 권한들입니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaPermissions",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:DeleteFunction",
                "lambda:GetFunction",
                "lambda:ListFunctions",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:InvokeFunction",
                "lambda:PublishLayerVersion",
                "lambda:DeleteLayerVersion"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3Permissions",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketPolicy",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetBucketVersioning",
                "s3:PutBucketVersioning"
            ],
            "Resource": [
                "arn:aws:s3:::bitcoin-auto-trader-*",
                "arn:aws:s3:::bitcoin-auto-trader-*/*"
            ]
        },
        {
            "Sid": "DynamoDBPermissions",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/bitcoin-auto-trader-*"
        },
        {
            "Sid": "SNSPermissions",
            "Effect": "Allow",
            "Action": [
                "sns:CreateTopic",
                "sns:DeleteTopic",
                "sns:GetTopicAttributes",
                "sns:SetTopicAttributes",
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:Publish",
                "sns:ListTopics"
            ],
            "Resource": "arn:aws:sns:*:*:bitcoin-auto-trader-*"
        },
        {
            "Sid": "CloudWatchPermissions",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:DeleteLogGroup"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/bitcoin-auto-trader-*"
        },
        {
            "Sid": "EventBridgePermissions",
            "Effect": "Allow",
            "Action": [
                "events:PutRule",
                "events:DeleteRule",
                "events:DescribeRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "events:ListRules",
                "events:ListTargetsByRule"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudFormationPermissions",
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:UpdateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ValidateTemplate",
                "cloudformation:ListStacks",
                "cloudformation:ListStackResources"
            ],
            "Resource": "arn:aws:cloudformation:*:*:stack/bitcoin-auto-trader-*/*"
        },
        {
            "Sid": "IAMPermissions",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/bitcoin-auto-trader-*",
                "arn:aws:iam::*:policy/bitcoin-auto-trader-*"
            ]
        }
    ]
}
```

**정책 파일 생성 및 적용:**

```bash
# 위 JSON을 파일로 저장
cat > minimal-iam-policy.json << 'EOF'
{위의 JSON 내용}
EOF

# 최소 권한 정책 생성
aws iam create-policy \
    --policy-name BitcoinTraderMinimalPolicy \
    --policy-document file://minimal-iam-policy.json

# 최소 권한 연결
aws iam attach-user-policy \
    --user-name bitcoin-trader-deployer \
    --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/BitcoinTraderMinimalPolicy
```

### 2. 권한 확인 및 검증

```bash
# 현재 사용자 확인
aws sts get-caller-identity

# 사용자 권한 확인
aws iam list-attached-user-policies --user-name bitcoin-trader-deployer

# 액세스 키 상태 확인
aws iam list-access-keys --user-name bitcoin-trader-deployer
```

### 3. GitHub Secrets 설정 방법

Repository > Settings > Secrets and variables > Actions에서 다음을 추가:

| Secret Name | 설명 | 예시 |
|-------------|------|------|
| `AWS_ACCESS_KEY_ID` | IAM 사용자의 액세스 키 | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM 사용자의 시크릿 키 | `wJalr...` |
| `BINANCE_API_KEY` | 바이낸스 API 키 | `NhqP...` |
| `BINANCE_SECRET` | 바이낸스 시크릿 키 | `lsb...` |

### 4. 권한 트러블슈팅

#### 권한 부족 오류 해결
```bash
# CloudFormation 권한 오류
aws cloudformation describe-stacks --stack-name bitcoin-auto-trader-dev

# Lambda 권한 오류
aws lambda get-function --function-name bitcoin-auto-trader-dev-trade

# S3 권한 오류
aws s3 ls s3://bitcoin-auto-trader-dev-state-store
```

#### 권한 최적화 (보안 강화)
- 특정 리소스에만 권한 제한
- 조건부 정책 사용 (IP, MFA 등)
- 정기적인 권한 감사 및 갱신

**📚 상세 권한 정보**: [`docs/IAM_POLICY.md`](docs/IAM_POLICY.md) 참조

---

## 🔄 GitHub Actions 자동 배포

master 브랜치에 push하면 자동으로 AWS Lambda에 배포됩니다.

### 1. 사전 준비사항

⚠️ **반드시 위의 [🔐 AWS IAM 권한 설정](#-aws-iam-권한-설정) 섹션을 먼저 완료하세요.**

### 2. GitHub Secrets 설정

Repository Settings > Secrets and variables > Actions에서 다음 변수들을 설정하세요:

| Secret Name | 값 | 설명 |
|-------------|-----|------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM 사용자의 액세스 키 |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | IAM 사용자의 시크릿 키 |
| `BINANCE_API_KEY` | `NhqP...` | 바이낸스 API 키 (현물 거래 권한) |
| `BINANCE_SECRET` | `lsb...` | 바이낸스 시크릿 키 |

**💡 Tips:**
- SNS 토픽은 배포 시 자동으로 생성되므로 ARN을 직접 설정할 필요 없습니다
- API 키는 바이낸스에서 **현물 거래 권한만** 활성화하세요
- 실제 값은 절대 코드에 직접 입력하지 마세요

### 3. 자동 배포 프로세스

```bash
# 코드 변경 후 master에 push
git add .
git commit -m "Update trading strategy"
git push origin master

# GitHub Actions가 자동으로:
# 1. 코드 품질 검사 (lint, format)
# 2. 설정 파일 유효성 검사
# 3. AWS Lambda 배포
```

### 4. 배포 상태 확인

```bash
# GitHub Actions 로그 확인
# Repository > Actions 탭에서 워크플로우 실행 상태 확인

# 배포 후 AWS 리소스 확인
aws cloudformation describe-stacks --stack-name bitcoin-auto-trader-dev

# Lambda 함수 테스트
aws lambda invoke --function-name bitcoin-auto-trader-dev-trade response.json
```

---

## ☁️ 수동 AWS 배포

### 1. AWS 계정 설정

```bash
# AWS CLI 설치 및 설정
aws configure
```

### 2. 배포 실행

```bash
# 환경 변수 export
export BINANCE_API_KEY=your_api_key
export BINANCE_SECRET=your_secret_key

# Serverless 배포 (SNS 토픽 자동 생성)
npx serverless deploy --stage dev

# 또는 npm script 사용
npm run deploy
```

### 3. 배포 후 확인

```bash
# Lambda 함수 로그 확인
npm run logs

# 수동 실행 테스트
npm run invoke
```

---

## 📊 모니터링

### 거래 상태 확인
거래 상태는 S3 버킷에 JSON 형태로 저장됩니다:

```json
{
  "trading_pair": "BTC/USDT",
  "position": {
    "buy_price": 45000.0,
    "buy_amount": 0.000444,
    "buy_time": "2024-01-15T10:30:00",
    "order_id": "12345"
  },
  "last_trade": {
    "buy_price": 44000.0,
    "sell_price": 45500.0,
    "profit": 1.2,
    "profit_rate": 0.0341
  },
  "total_trades": 10,
  "total_profit": 15.67,
  "updated_at": "2024-01-15T11:00:00"
}
```

### AWS CloudWatch
- Lambda 함수 실행 로그
- 에러 및 성능 모니터링
- 알람 설정 가능

---

## ⚠️ 주의사항

### 1. 실거래 전 확인사항
- 바이낸스 계정에 최소 100 USDT 입금
- API 키 권한이 **현물 거래**로 제한되어 있는지 확인
- 테스트넷에서 충분한 검증 후 실거래 시작

### 2. 리스크 관리
- 소액으로 시작하여 점진적으로 증액
- 정기적인 백테스트로 전략 성과 검증
- 시장 변동성이 클 때는 일시 중단 고려

### 3. 비용 관리
- AWS Lambda: 월 100만 회 무료 (이후 $0.20/100만 회)
- S3: 월 5GB 무료 (이후 $0.023/GB)
- 바이낸스 거래 수수료: 0.1% (VIP 레벨에 따라 할인)

---

## 🛠️ 개발 및 커스터마이징

### 설정 파일 기반 관리
이제 코드 수정 없이 `config.json` 파일이나 CLI 도구로 모든 설정을 관리할 수 있습니다:

```bash
# 프리셋 적용
npm run config -- preset balanced

# 개별 설정 변경
npm run config -- set sma_short 10
npm run config -- set sma_long 30
npm run config -- set trade_amount 50
npm run config -- set profit_threshold 0.004
```

**사용 가능한 프리셋:**
- `conservative`: 안전한 거래 (SMA 10/30, 20 USDT, 0.5% 수익률)
- `balanced`: 균형잡힌 거래 (SMA 7/25, 50 USDT, 0.3% 수익률) - **권장**
- `aggressive`: 공격적 거래 (SMA 5/15, 90 USDT, 0.2% 수익률)

### 다른 코인 지원
`symbol = 'BTC/USDT'`를 다른 거래쌍으로 변경 가능:
- ETH/USDT
- BNB/USDT
- ADA/USDT 등

### 알림 기능 추가
Discord, Slack, 텔레그램 등으로 거래 알림을 받을 수 있도록 확장 가능

---

## 📚 문서 구조

```
docs/
├── IAM_POLICY.md              # AWS IAM 권한 설정 가이드
├── DEPLOYMENT_GUIDE.md        # 상세 배포 가이드
└── minimal-iam-policy.json    # 최소 권한 IAM 정책 JSON
```

### 주요 문서

- **[IAM 권한 가이드](docs/IAM_POLICY.md)**: AWS 배포에 필요한 상세 권한 설정
- **[배포 가이드](docs/DEPLOYMENT_GUIDE.md)**: 단계별 배포 과정 및 트러블슈팅
- **[IAM 정책 JSON](docs/minimal-iam-policy.json)**: 최소 권한 정책 파일

---

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

## ⚡ 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/python-binance-auto-trade.git
cd python-binance-auto-trade

# 2. 의존성 설치
poetry install && npm install

# 3. 환경 변수 설정
cp env.example .env
# .env 파일에 바이낸스 API 키 입력

# 4. 백테스트 실행
npm run backtest:chart

# 5. AWS 배포
export BINANCE_API_KEY=your_key
export BINANCE_SECRET=your_secret
npm run deploy
```

**⚠️ 실거래 전 반드시 백테스트와 소액 테스트를 진행하세요!**