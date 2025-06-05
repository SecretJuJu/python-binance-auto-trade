# 🐳 AWS Fargate 배포 가이드

Lambda Layer 크기 제한 문제를 해결하기 위해 AWS Fargate를 사용한 컨테이너 기반 배포 방법입니다.

## 🔄 Lambda vs Fargate 비교

| 항목 | Lambda | Fargate |
|------|--------|---------|
| **의존성 크기** | 250MB 제한 | 제한 없음 |
| **실행 시간** | 15분 제한 | 제한 없음 |
| **메모리** | 10GB 제한 | 30GB까지 |
| **비용** | 실행시간 기준 | 실행시간 + 메모리 |
| **콜드 스타트** | 있음 | 컨테이너 시작 시간 |
| **라이브러리** | 제한적 | 자유로움 |

## 🏗️ 아키텍처

```
EventBridge (10분마다) 
    ↓
ECS Fargate Task 실행
    ↓
거래 로직 처리
    ↓
S3에 상태 저장
    ↓
SNS 알림 발송
    ↓
Task 종료
```

## 📋 사전 준비

### 1. 필수 도구 설치

```bash
# AWS CDK 설치
npm install -g aws-cdk

# Docker 설치 (macOS)
brew install docker

# Python 의존성 설치
pip install aws-cdk-lib constructs
```

### 2. AWS 자격 증명 설정

```bash
aws configure
# 또는
export AWS_PROFILE=your-profile
```

### 3. 환경 변수 설정

```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET="your_secret_key"
export AWS_REGION="ap-northeast-2"  # 선택사항
```

## 🚀 배포 실행

### 원클릭 배포

```bash
./deploy-fargate.sh
```

### 단계별 배포

#### 1. Secrets Manager에 API 키 저장

```bash
aws secretsmanager create-secret \
    --name "bitcoin-trading/binance" \
    --description "Binance API credentials" \
    --secret-string "{\"api_key\":\"$BINANCE_API_KEY\",\"secret\":\"$BINANCE_SECRET\"}"
```

#### 2. CDK 인프라 배포

```bash
cd cdk
pip install -r requirements.txt
cdk bootstrap  # 처음 한 번만
cdk deploy
```

#### 3. Docker 이미지 빌드 및 푸시

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
    docker login --username AWS --password-stdin <ECR_URI>

# 이미지 빌드 및 푸시
docker build -t bitcoin-auto-trader .
docker tag bitcoin-auto-trader:latest <ECR_URI>:latest
docker push <ECR_URI>:latest
```

#### 4. 테스트 실행

```bash
# 수동으로 태스크 실행하여 테스트
aws ecs run-task \
    --cluster bitcoin-trading-cluster \
    --task-definition bitcoin-trading-task \
    --launch-type FARGATE
```

## 📊 모니터링

### CloudWatch 로그 확인

```bash
# 실시간 로그 스트림
aws logs tail /aws/ecs/bitcoin-trading --follow

# 특정 기간 로그 조회
aws logs filter-log-events \
    --log-group-name /aws/ecs/bitcoin-trading \
    --start-time $(date -d '1 hour ago' +%s)000
```

### ECS 태스크 상태 확인

```bash
# 실행 중인 태스크 조회
aws ecs list-tasks --cluster bitcoin-trading-cluster

# 태스크 상세 정보
aws ecs describe-tasks \
    --cluster bitcoin-trading-cluster \
    --tasks <task-arn>
```

## 🔧 설정 변경

### 1. 거래 설정 변경

```bash
# config.json 수정 후 이미지 재빌드
vim config.json
docker build -t bitcoin-auto-trader .
docker push <ECR_URI>:latest
```

### 2. 스케줄 변경

`cdk/bitcoin_trading_stack.py`에서 스케줄 수정:

```python
schedule=events.Schedule.rate(Duration.minutes(5))  # 5분으로 변경
```

### 3. 리소스 할당 변경

```python
# Task Definition에서 메모리/CPU 조정
memory_limit_mib=2048,  # 2GB로 증가
cpu=1024               # 1 vCPU로 증가
```

## 💰 비용 최적화

### 예상 비용 (월간)

```
Fargate 비용:
- 0.5 vCPU, 1GB RAM
- 실행시간: 10분마다 × 평균 30초 = 월 24시간
- 비용: ~$2-3/월

추가 비용:
- ECR: ~$0.10/월
- CloudWatch Logs: ~$0.50/월
- SNS: ~$0.50/월
```

### 비용 절약 팁

1. **스팟 인스턴스 사용** (CDK에서 설정 가능)
2. **로그 보존 기간 단축** (1개월 → 1주일)
3. **불필요한 알림 비활성화**

## 🔄 업데이트 및 배포

### 코드 변경 시

```bash
# 이미지 재빌드 및 푸시
docker build -t bitcoin-auto-trader .
docker push <ECR_URI>:latest

# 새 태스크 정의 등록 (자동)
# 다음 스케줄 실행 시 새 이미지 사용
```

### 인프라 변경 시

```bash
cd cdk
cdk diff    # 변경 사항 확인
cdk deploy  # 인프라 업데이트
```

## 🗑️ 리소스 정리

### 전체 스택 삭제

```bash
cd cdk
cdk destroy

# Secrets Manager 시크릿 삭제
aws secretsmanager delete-secret \
    --secret-id "bitcoin-trading/binance" \
    --force-delete-without-recovery
```

### 선택적 정리

```bash
# ECR 이미지만 삭제
aws ecr batch-delete-image \
    --repository-name bitcoin-auto-trader \
    --image-ids imageTag=latest
```

## 🚨 트러블슈팅

### 1. Task 실행 실패

```bash
# 태스크 실패 원인 확인
aws ecs describe-tasks \
    --cluster bitcoin-trading-cluster \
    --tasks <failed-task-arn>
```

**일반적인 원인:**
- Secrets Manager 권한 부족
- VPC/서브넷 설정 오류  
- Docker 이미지 오류

### 2. Docker 빌드 실패

```bash
# 로컬에서 테스트
docker run -it --rm \
    -e BINANCE_API_KEY="test" \
    -e BINANCE_SECRET="test" \
    bitcoin-auto-trader
```

### 3. 스케줄 실행 안 됨

```bash
# EventBridge 규칙 상태 확인
aws events describe-rule --name bitcoin-trading-schedule
```

## 📚 추가 참고자료

- [AWS ECS Fargate 가이드](https://docs.aws.amazon.com/ecs/latest/userguide/what-is-fargate.html)
- [AWS CDK Python 문서](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [EventBridge 스케줄링](https://docs.aws.amazon.com/eventbridge/latest/userguide/scheduled-events.html)

---

**🎯 Fargate 배포의 장점:**
- ✅ Lambda 크기 제한 없음
- ✅ 모든 Python 라이브러리 사용 가능
- ✅ 더 강력한 컴퓨팅 리소스
- ✅ 더 나은 로그 및 모니터링 