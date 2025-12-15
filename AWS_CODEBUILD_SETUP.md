# AWS CodeBuild Setup Guide

This guide shows how to use **AWS CodeBuild** to build your Docker image and push it to ECR, instead of using GitHub Actions.

## 📋 Prerequisites

- AWS CLI configured
- ECR repository created (run `./deploy-fargate.sh` option 2)
- Your code in a Git repository (GitHub, CodeCommit, Bitbucket, etc.)

## 🚀 Step-by-Step Setup

### Step 1: Create IAM Role for CodeBuild

```bash
# Create trust policy for CodeBuild
cat > /tmp/codebuild-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
    --role-name CodeBuildServiceRole-RateAudit \
    --assume-role-policy-document file:///tmp/codebuild-trust-policy.json

# Create policy for CodeBuild permissions
cat > /tmp/codebuild-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Attach the policy
aws iam put-role-policy \
    --role-name CodeBuildServiceRole-RateAudit \
    --policy-name CodeBuildPolicy \
    --policy-document file:///tmp/codebuild-policy.json
```

### Step 2: Create CodeBuild Project via AWS Console

1. **Go to AWS CodeBuild Console**: https://console.aws.amazon.com/codesuite/codebuild/projects

2. **Click "Create build project"**

3. **Project configuration:**
   - **Project name**: `rate-audit-analyser-build`
   - **Description**: Build and push Rate Audit Analyser to ECR

4. **Source:**
   - **Source provider**: Choose your Git provider (GitHub, CodeCommit, etc.)
   - **Repository**: Select or connect your repository
   - **Branch**: `main` (or your default branch)

5. **Environment:**
   - **Environment image**: Managed image
   - **Operating system**: Ubuntu
   - **Runtime**: Standard
   - **Image**: `aws/codebuild/standard:7.0` (latest)
   - **Image version**: Always use the latest
   - **Privileged**: ✅ **Check this box** (required for Docker builds)
   - **Service role**: `CodeBuildServiceRole-RateAudit`

6. **Environment variables:**
   Add these:
   - `AWS_ACCOUNT_ID`: Your AWS account ID (get with `aws sts get-caller-identity --query Account --output text`)
   - `AWS_DEFAULT_REGION`: `us-east-1` (or your region)

7. **Buildspec:**
   - **Build specifications**: Use a buildspec file
   - **Buildspec name**: `buildspec.yml`

8. **Artifacts:**
   - **Type**: No artifacts (or S3 if you want to save build outputs)

9. **Logs:**
   - **CloudWatch Logs**: ✅ Enabled
   - **Group name**: `/aws/codebuild/rate-audit-analyser`

10. **Click "Create build project"**

### Step 3: Create CodeBuild Project via AWS CLI

Alternatively, use this command:

```bash
# Get your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Create the build project
aws codebuild create-project \
    --name rate-audit-analyser-build \
    --source type=GITHUB,location=https://github.com/YOUR_USERNAME/RateAuditAnalyser.git \
    --artifacts type=NO_ARTIFACTS \
    --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables="[{name=AWS_ACCOUNT_ID,value=$AWS_ACCOUNT_ID},{name=AWS_DEFAULT_REGION,value=$AWS_REGION}]" \
    --service-role arn:aws:iam::$AWS_ACCOUNT_ID:role/CodeBuildServiceRole-RateAudit \
    --region $AWS_REGION
```

**Replace** `YOUR_USERNAME/RateAuditAnalyser` with your actual repository path.

### Step 4: Trigger a Build

#### Option A: Manual Build (Console)
1. Go to CodeBuild console
2. Select your project
3. Click **"Start build"**

#### Option B: Manual Build (CLI)
```bash
aws codebuild start-build \
    --project-name rate-audit-analyser-build \
    --region us-east-1
```

#### Option C: Automatic Builds (Webhook)
Set up a webhook to automatically build on git push:

```bash
aws codebuild create-webhook \
    --project-name rate-audit-analyser-build \
    --filter-groups "[[{\"type\":\"EVENT\",\"pattern\":\"PUSH\"},{\"type\":\"HEAD_REF\",\"pattern\":\"refs/heads/main\"}]]" \
    --region us-east-1
```

Now every push to the `main` branch will trigger a build automatically!

### Step 5: Monitor the Build

**Via Console:**
1. Go to CodeBuild → Build projects → rate-audit-analyser-build
2. Click on the running build
3. View **Build logs** tab for real-time output

**Via CLI:**
```bash
# Get the latest build ID
BUILD_ID=$(aws codebuild list-builds-for-project \
    --project-name rate-audit-analyser-build \
    --region us-east-1 \
    --query 'ids[0]' \
    --output text)

# Get build status
aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region us-east-1 \
    --query 'builds[0].{Status:buildStatus,Phase:currentPhase}'

# Tail logs
aws logs tail /aws/codebuild/rate-audit-analyser --follow --region us-east-1
```

## ✅ Verification

After a successful build:

1. **Check ECR**: Your image should be in ECR
   ```bash
   aws ecr describe-images \
       --repository-name rate-audit-analyser \
       --region us-east-1
   ```

2. **ECS service updates automatically**: The buildspec includes a command to force ECS to redeploy

3. **Access your app**: Get the public IP (see QUICKSTART_FARGATE.md)

## 🔄 CI/CD Pipeline (Optional)

For a complete CI/CD pipeline, create a **CodePipeline**:

1. **Go to CodePipeline console**
2. **Create pipeline**
3. **Source**: Your Git repository
4. **Build**: CodeBuild project (rate-audit-analyser-build)
5. **Deploy**: ECS (cluster: rate-audit-cluster, service: rate-audit-service)

This creates a full automated pipeline: Git push → Build → Deploy to ECS.

## 🆘 Troubleshooting

**Build fails with "Cannot connect to Docker daemon":**
- Ensure **Privileged mode** is enabled in environment settings

**Build fails with ECR authorization error:**
- Check IAM role has ECR permissions
- Verify `AWS_ACCOUNT_ID` environment variable is set correctly

**ECS doesn't update after build:**
- Check IAM role has `ecs:UpdateService` permission
- Verify cluster and service names match in buildspec.yml

## 💰 Cost

- **CodeBuild**: First 100 build minutes/month free, then ~$0.005/minute
- **Much cheaper than GitHub Actions for private repos**
- **Keeps everything in AWS ecosystem**

## 📚 Additional Resources

- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [Buildspec Reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- [Docker in CodeBuild](https://docs.aws.amazon.com/codebuild/latest/userguide/sample-docker.html)
