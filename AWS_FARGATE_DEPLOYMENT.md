# AWS Fargate Deployment Guide - Rate Audit Analyser

This guide provides step-by-step instructions to deploy your Rate Audit Analyser application to AWS Fargate without needing local Docker.

## 🎯 Overview

We'll deploy using:
- **Amazon ECR** - Container registry
- **Amazon ECS Fargate** - Serverless container compute
- **Application Load Balancer** - Traffic distribution
- **AWS Secrets Manager** - Secure credential storage
- **AWS CodeBuild** - Automated cloud builds (bypasses local Docker issues)

## 📋 Prerequisites

1. **AWS Account** with administrative access
2. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```
3. **Git repository** (GitHub, CodeCommit, Bitbucket, etc.)
4. **Domain name** (optional, for custom URL)

## 🚀 Deployment Steps

### Step 1: Set Up AWS Credentials

First, configure your AWS CLI if you haven't already:

```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Output format: `json`

Verify it works:
```bash
aws sts get-caller-identity
```

### Step 2: Store Secrets in AWS Secrets Manager

Store your API keys securely:

```bash
# Set your region (change as needed)
export AWS_REGION=us-east-1

# Store Google API Key
aws secretsmanager create-secret \
    --name rate-audit/google-api-key \
    --description "Google API Key for Rate Audit Analyser" \
    --secret-string "AIzaSyB7E7bBohq5uR9wApCSAyPima-jh2oXOSg" \
    --region $AWS_REGION

# Store MCP API Key
aws secretsmanager create-secret \
    --name rate-audit/mcp-api-key \
    --description "MCP API Key for Rate Audit Analyser" \
    --secret-string "eyJhbGci" \
    --region $AWS_REGION

# Store LangChain API Key (optional)
aws secretsmanager create-secret \
    --name rate-audit/langchain-api-key \
    --description "LangChain API Key for Rate Audit Analyser" \
    --secret-string "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" \
    --region $AWS_REGION
```

> **Note**: Replace the secret values with your actual API keys from the `.env` file.

### Step 3: Create ECR Repository

Create a repository to store your Docker images:

```bash
aws ecr create-repository \
    --repository-name rate-audit-analyser \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true
```

Note the repository URI from the output (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/rate-audit-analyser`)

### Step 4: Set Up AWS CodeBuild for Automated Builds

Since you can't build locally, use AWS CodeBuild to build in the cloud.

See the complete setup guide: [AWS_CODEBUILD_SETUP.md](./AWS_CODEBUILD_SETUP.md)

**Quick summary:**

1. Create IAM role for CodeBuild with ECR and ECS permissions
2. Create CodeBuild project pointing to your repository
3. Enable **Privileged mode** (required for Docker builds)
4. Set up webhook for automatic builds on git push

The `buildspec.yml` file is already configured and will:
- Build the Docker image
- Push it to ECR
- Update the ECS service automatically

### Step 5: Create VPC and Networking (If Needed)

If you don't have a VPC with subnets:

```bash
# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

echo "Using VPC: $VPC_ID"

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $AWS_REGION)

echo "Subnets: $SUBNET_IDS"
```

### Step 6: Create Security Group

```bash
# Create security group
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name rate-audit-sg \
    --description "Security group for Rate Audit Analyser" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text)

echo "Security Group ID: $SECURITY_GROUP_ID"

# Allow inbound traffic on port 8501 (Streamlit)
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 8501 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

# Allow outbound traffic (all)
aws ec2 authorize-security-group-egress \
    --group-id $SECURITY_GROUP_ID \
    --protocol -1 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || true
```

### Step 7: Create IAM Role for ECS Task

```bash
# Create trust policy
cat > ecs-task-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
    --role-name ecsTaskExecutionRole-RateAudit \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-RateAudit \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create policy for Secrets Manager access
cat > secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:$AWS_REGION:*:secret:rate-audit/*"
      ]
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
    --policy-name RateAuditSecretsPolicy \
    --policy-document file://secrets-policy.json

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-RateAudit \
    --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/RateAuditSecretsPolicy
```

### Step 8: Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name rate-audit-cluster \
    --region $AWS_REGION \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=0 \
        capacityProvider=FARGATE_SPOT,weight=4,base=0
```

### Step 9: Register ECS Task Definition

Get your AWS Account ID and ECR repository URI:

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/rate-audit-analyser:latest"

echo "ECR Repository: $ECR_REPO"
```

Create the task definition file (this is already in your repository as `ecs-task-definition.json`):

```bash
# Register the task definition
aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition.json \
    --region $AWS_REGION
```

### Step 10: Create Application Load Balancer (Optional but Recommended)

```bash
# Convert SUBNET_IDS to array format
SUBNET_ARRAY=$(echo $SUBNET_IDS | tr '\t' ' ')

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name rate-audit-alb \
    --subnets $SUBNET_ARRAY \
    --security-groups $SECURITY_GROUP_ID \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

echo "ALB ARN: $ALB_ARN"

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
    --name rate-audit-tg \
    --protocol HTTP \
    --port 8501 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /_stcore/health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Target Group ARN: $TG_ARN"

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $AWS_REGION

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' \
    --output text \
    --region $AWS_REGION)

echo "🌐 Your application will be available at: http://$ALB_DNS"
```

### Step 11: Create ECS Service

```bash
# Convert SUBNET_IDS to comma-separated format
SUBNETS_CSV=$(echo $SUBNET_IDS | tr '\t' ',')

# Create the service
aws ecs create-service \
    --cluster rate-audit-cluster \
    --service-name rate-audit-service \
    --task-definition rate-audit-task:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS_CSV],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TG_ARN,containerName=rate-audit-analyser,containerPort=8501" \
    --health-check-grace-period-seconds 60 \
    --region $AWS_REGION
```

### Step 12: Monitor Deployment

```bash
# Watch service status
watch -n 5 "aws ecs describe-services \
    --cluster rate-audit-cluster \
    --services rate-audit-service \
    --region $AWS_REGION \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'"

# View logs (after container starts)
aws logs tail /ecs/rate-audit-task --follow --region $AWS_REGION
```

## ✅ Verification

1. **Check service health**:
   ```bash
   aws ecs describe-services \
       --cluster rate-audit-cluster \
       --services rate-audit-service \
       --region $AWS_REGION
   ```

2. **Access your application**:
   - Via ALB: `http://<ALB_DNS>`
   - Via public IP (if no ALB): Get the task's public IP from ECS console

3. **View logs**:
   ```bash
   aws logs tail /ecs/rate-audit-task --follow --region $AWS_REGION
   ```

## 🔄 Updates and Redeployment

When you push changes to your Git repository:

1. **Automatic**: If you set up CodeBuild webhook, it triggers automatically on git push
2. **Manual**: Trigger a build in CodeBuild console or via CLI:
   ```bash
   aws codebuild start-build \
       --project-name rate-audit-analyser-build \
       --region us-east-1
   ```

The build will automatically update the ECS service with the new image.

## 💰 Cost Optimization

- **Use Fargate Spot**: Already configured in default capacity provider strategy (80% spot, 20% on-demand)
- **Right-size resources**: Adjust CPU/memory in task definition based on actual usage
- **Enable auto-scaling**: Scale based on CPU/memory metrics
- **Stop when not needed**: Set desired count to 0 to stop charges

## 🧹 Cleanup

To remove all resources:

```bash
# Delete ECS service
aws ecs update-service \
    --cluster rate-audit-cluster \
    --service rate-audit-service \
    --desired-count 0 \
    --region $AWS_REGION

aws ecs delete-service \
    --cluster rate-audit-cluster \
    --service rate-audit-service \
    --force \
    --region $AWS_REGION

# Delete cluster
aws ecs delete-cluster \
    --cluster rate-audit-cluster \
    --region $AWS_REGION

# Delete ALB and target group
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN --region $AWS_REGION
aws elbv2 delete-target-group --target-group-arn $TG_ARN --region $AWS_REGION

# Delete security group
aws ec2 delete-security-group --group-id $SECURITY_GROUP_ID --region $AWS_REGION

# Delete ECR repository
aws ecr delete-repository \
    --repository-name rate-audit-analyser \
    --force \
    --region $AWS_REGION

# Delete secrets
aws secretsmanager delete-secret --secret-id rate-audit/google-api-key --force-delete-without-recovery --region $AWS_REGION
aws secretsmanager delete-secret --secret-id rate-audit/mcp-api-key --force-delete-without-recovery --region $AWS_REGION
aws secretsmanager delete-secret --secret-id rate-audit/langchain-api-key --force-delete-without-recovery --region $AWS_REGION
```

## 📚 Alternative: Simple One-Command Deployment Script

I've created a simplified script that automates most of these steps. See `deploy-fargate.sh` in this repository.

```bash
chmod +x deploy-fargate.sh
./deploy-fargate.sh
```

## 🆘 Troubleshooting

### Container won't start
- Check CloudWatch logs: `/ecs/rate-audit-task`
- Verify secrets exist in Secrets Manager
- Check IAM role permissions

### Can't access application
- Verify security group allows inbound traffic on port 8501
- Check ALB health checks are passing
- Ensure tasks have public IPs (or use NAT gateway for private subnets)

### Build fails in CodeBuild
- Check IAM role has ECR and ECS permissions
- Verify Privileged mode is enabled
- Review CodeBuild logs in CloudWatch

## 📖 Additional Resources

- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ECS Task Definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
