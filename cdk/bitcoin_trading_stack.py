"""
Bitcoin Trading Bot - AWS CDK Stack
ECS Fargate + EventBridge 스케줄링
"""

from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_sns as sns,
    aws_ecr as ecr,
)
from constructs import Construct


class BitcoinTradingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 생성 (또는 기본 VPC 사용)
        vpc = ec2.Vpc.from_lookup(
            self, "VPC",
            is_default=True
        )

        # ECS 클러스터 생성
        cluster = ecs.Cluster(
            self, "BitcoinTradingCluster",
            vpc=vpc,
            cluster_name="bitcoin-trading-cluster"
        )

        # ECR 리포지토리 생성
        repository = ecr.Repository(
            self, "BitcoinTradingRepo",
            repository_name="bitcoin-auto-trader",
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 most recent images"
                )
            ]
        )

        # S3 버킷 (거래 상태 저장)
        state_bucket = s3.Bucket(
            self, "TradingStateBucket",
            bucket_name=f"bitcoin-trading-state-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # SNS 토픽 (알림)
        notification_topic = sns.Topic(
            self, "TradingNotificationTopic",
            topic_name="bitcoin-trading-alerts",
            display_name="Bitcoin Trading Bot Alerts"
        )

        # CloudWatch 로그 그룹
        log_group = logs.LogGroup(
            self, "TradingLogGroup",
            log_group_name="/aws/ecs/bitcoin-trading",
            retention=logs.RetentionDays.ONE_MONTH
        )

        # Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, "TradingTaskDef",
            family="bitcoin-trading-task",
            memory_limit_mib=1024,
            cpu=512
        )

        # Task Role에 필요한 권한 부여
        task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                resources=[f"{state_bucket.bucket_arn}/*"]
            )
        )

        task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=[notification_topic.topic_arn]
            )
        )

        # 컨테이너 정의
        container = task_definition.add_container(
            "TradingContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, "latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="bitcoin-trading",
                log_group=log_group
            ),
            environment={
                "SNS_TOPIC_ARN": notification_topic.topic_arn,
                "S3_BUCKET": state_bucket.bucket_name,
                "AWS_DEFAULT_REGION": self.region,
                "NOTIFY_ON_SUCCESS": "false"  # 필요시 true로 변경
            },
            secrets={
                "BINANCE_API_KEY": ecs.Secret.from_secrets_manager(
                    "bitcoin-trading/binance",
                    field="api_key"
                ),
                "BINANCE_SECRET": ecs.Secret.from_secrets_manager(
                    "bitcoin-trading/binance", 
                    field="secret"
                )
            }
        )

        # EventBridge 규칙 (10분마다 실행)
        schedule_rule = events.Rule(
            self, "TradingScheduleRule",
            rule_name="bitcoin-trading-schedule",
            description="Run Bitcoin Trading Bot every 10 minutes",
            schedule=events.Schedule.rate(Duration.minutes(10))
        )

        # ECS Task를 EventBridge 타겟으로 추가
        schedule_rule.add_target(
            events_targets.EcsTask(
                cluster=cluster,
                task_definition=task_definition,
                subnet_selection=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                assign_public_ip=True,
                platform_version=ecs.FargatePlatformVersion.LATEST
            )
        )

        # Outputs
        from aws_cdk import CfnOutput
        
        CfnOutput(
            self, "ECRRepositoryURI",
            value=repository.repository_uri,
            description="ECR Repository URI for Docker images"
        )

        CfnOutput(
            self, "SNSTopicArn", 
            value=notification_topic.topic_arn,
            description="SNS Topic ARN for notifications"
        )

        CfnOutput(
            self, "S3BucketName",
            value=state_bucket.bucket_name,
            description="S3 Bucket for trading state storage"
        ) 