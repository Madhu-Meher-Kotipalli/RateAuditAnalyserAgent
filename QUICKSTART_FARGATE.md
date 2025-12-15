# 🚀 Quick Start: Deploy to AWS Fargate

Get your Rate Audit Analyser running on AWS Fargate in **4 simple steps** (no local Docker required!).

## ✅ Prerequisites

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Your code in a Git repository (GitHub, CodeCommit, Bitbucket, etc.)

## 📋 4-Step Deployment

### Step 1: Configure AWS CLI

```bash
aws configure
```

Enter your AWS credentials and preferred region (e.g., `us-east-1`).

### Step 2: Run the Deployment Script

```bash
cd /home/k-madhu/Audintel/RateAuditAnalyser
./deploy-fargate.sh
```

Select **Option 1** (Full deployment) and follow the prompts.

The script will:
- ✅ Create ECR repository for your Docker images
- ✅ Store API keys in AWS Secrets Manager
- ✅ Set up IAM roles and permissions
- ✅ Create ECS Fargate cluster
- ✅ Deploy your application

### Step 3: Set Up AWS CodeBuild

Follow the guide in [AWS_CODEBUILD_SETUP.md](./AWS_CODEBUILD_SETUP.md) to set up automated builds:

1. Create IAM role for CodeBuild
2. Create CodeBuild project pointing to your repository
3. Enable **Privileged mode** (required for Docker)
4. Set up webhook for automatic builds on git push

This will build your Docker image in the cloud and push it to ECR automatically.

### Step 4: Access Your Application

The deployment script will show you the public IP:

```
🌐 Your application is available at: http://X.X.X.X:8501
```

Open this URL in your browser!

## 🔍 Monitoring

**Check deployment status:**
```bash
aws ecs describe-services \
  --cluster rate-audit-cluster \
  --services rate-audit-service \
  --region us-east-1
```

**View logs:**
```bash
aws logs tail /ecs/rate-audit-task --follow --region us-east-1
```

## 🆘 Troubleshooting

**Service not starting?**
- Check CloudWatch logs: `/ecs/rate-audit-task`
- Verify secrets exist in AWS Secrets Manager
- Ensure GitHub Actions completed successfully

**Can't access application?**
- Wait 2-3 minutes for initial startup
- Verify security group allows inbound traffic on port 8501
- Check that task has a public IP assigned

## 📚 Need More Details?

See [AWS_FARGATE_DEPLOYMENT.md](./AWS_FARGATE_DEPLOYMENT.md) for comprehensive documentation.

## 🧹 Cleanup (Stop Billing)

To remove all AWS resources and stop charges:

```bash
./deploy-fargate.sh
```

Select **Option 6** (Cleanup all resources).

---

**Estimated Time**: 10-15 minutes  
**Estimated Cost**: ~$10-20/month for light usage (using Fargate Spot)
