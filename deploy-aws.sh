#!/bin/bash

# AWS Deployment Quick Start Script for Rate Audit Analyser
# This script helps you deploy the application to AWS

set -e

echo "🚀 Rate Audit Analyser - AWS Deployment Helper"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

# Menu selection
echo "Select deployment option:"
echo "1) AWS App Runner (Easiest - Recommended for quick start)"
echo "2) Amazon ECS Fargate (Production - Full control)"
echo "3) EC2 with Docker (Custom setup)"
echo "4) Test locally with Docker"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${BLUE}📦 Deploying to AWS App Runner${NC}"
        
        # Get AWS account ID
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        AWS_REGION=${AWS_REGION:-us-east-1}
        
        echo "AWS Account ID: $AWS_ACCOUNT_ID"
        echo "AWS Region: $AWS_REGION"
        
        # Create ECR repository
        echo ""
        echo "Creating ECR repository..."
        aws ecr create-repository --repository-name rate-audit-analyser --region $AWS_REGION 2>/dev/null || echo "Repository already exists"
        
        # Login to ECR
        echo ""
        echo "Logging in to ECR..."
        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
        
        # Build image
        echo ""
        echo "Building Docker image..."
        docker build -t rate-audit-analyser:latest .
        
        # Tag and push
        echo ""
        echo "Pushing to ECR..."
        docker tag rate-audit-analyser:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rate-audit-analyser:latest
        docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rate-audit-analyser:latest
        
        echo ""
        echo -e "${GREEN}✅ Image pushed successfully!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Go to AWS App Runner Console: https://console.aws.amazon.com/apprunner"
        echo "2. Click 'Create service'"
        echo "3. Select ECR repository: rate-audit-analyser:latest"
        echo "4. Configure:"
        echo "   - Port: 8501"
        echo "   - CPU: 1 vCPU"
        echo "   - Memory: 2 GB"
        echo "5. Add environment variables:"
        echo "   - GOOGLE_API_KEY"
        echo "   - MCP_API_KEY"
        echo "6. Health check path: /_stcore/health"
        echo "7. Click 'Create & deploy'"
        ;;
    
    2)
        echo -e "${BLUE}🐳 Deploying to Amazon ECS Fargate${NC}"
        
        # Get AWS account ID
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        AWS_REGION=${AWS_REGION:-us-east-1}
        
        echo "AWS Account ID: $AWS_ACCOUNT_ID"
        echo "AWS Region: $AWS_REGION"
        
        # Store secrets
        echo ""
        read -p "Enter your GOOGLE_API_KEY: " GOOGLE_API_KEY
        read -p "Enter your MCP_API_KEY: " MCP_API_KEY
        
        echo ""
        echo "Storing secrets in AWS Secrets Manager..."
        aws secretsmanager create-secret \
            --name rate-audit/google-api-key \
            --secret-string "$GOOGLE_API_KEY" \
            --region $AWS_REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id rate-audit/google-api-key \
            --secret-string "$GOOGLE_API_KEY" \
            --region $AWS_REGION
        
        aws secretsmanager create-secret \
            --name rate-audit/mcp-api-key \
            --secret-string "$MCP_API_KEY" \
            --region $AWS_REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id rate-audit/mcp-api-key \
            --secret-string "$MCP_API_KEY" \
            --region $AWS_REGION
        
        # Create ECR repository
        echo ""
        echo "Creating ECR repository..."
        aws ecr create-repository --repository-name rate-audit-analyser --region $AWS_REGION 2>/dev/null || echo "Repository already exists"
        
        # Login to ECR
        echo ""
        echo "Logging in to ECR..."
        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
        
        # Build and push
        echo ""
        echo "Building and pushing Docker image..."
        docker build -t rate-audit-analyser:latest .
        docker tag rate-audit-analyser:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rate-audit-analyser:latest
        docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rate-audit-analyser:latest
        
        echo ""
        echo -e "${GREEN}✅ Setup complete!${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  Manual steps required:${NC}"
        echo "1. Create ECS cluster: rate-audit-cluster"
        echo "2. Create task definition using the image:"
        echo "   $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rate-audit-analyser:latest"
        echo "3. Create ECS service with ALB"
        echo ""
        echo "See the full guide: aws_deployment_guide.md"
        ;;
    
    3)
        echo -e "${BLUE}💻 Generating EC2 deployment script${NC}"
        
        cat > deploy-ec2.sh <<'EOF'
#!/bin/bash
# Run this script on your EC2 instance

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository (update with your repo)
# git clone <your-repo-url>
# cd RateAuditAnalyser

# Create .env file (you need to add your keys)
cat > .env <<ENVEOF
GOOGLE_API_KEY=your-key-here
MCP_API_KEY=your-key-here
ENVEOF

echo "⚠️  Please edit .env file with your actual API keys"
echo ""
echo "Then run:"
echo "  docker-compose up -d"
EOF
        
        chmod +x deploy-ec2.sh
        echo -e "${GREEN}✅ Created deploy-ec2.sh${NC}"
        echo "Upload this script to your EC2 instance and run it"
        ;;
    
    4)
        echo -e "${BLUE}🧪 Testing locally with Docker${NC}"
        
        # Check if .env exists
        if [ ! -f .env ]; then
            echo -e "${RED}❌ .env file not found${NC}"
            echo "Creating .env from .env.example..."
            cp .env.example .env
            echo -e "${YELLOW}⚠️  Please edit .env with your API keys${NC}"
            exit 1
        fi
        
        echo "Building Docker image..."
        docker build -t rate-audit-analyser:latest .
        
        echo ""
        echo "Starting container..."
        docker run -p 8501:8501 --env-file .env rate-audit-analyser:latest &
        
        DOCKER_PID=$!
        
        echo ""
        echo -e "${GREEN}✅ Container started!${NC}"
        echo ""
        echo "Access the app at: http://localhost:8501"
        echo ""
        echo "Press Ctrl+C to stop"
        
        # Wait for Ctrl+C
        trap "docker stop \$(docker ps -q --filter ancestor=rate-audit-analyser:latest); exit" INT
        wait $DOCKER_PID
        ;;
    
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "Done! 🎉"
