#!/bin/bash

# deploy.sh - Production deployment script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Telegram Report Bot${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}📝 Please create .env file with required configuration:${NC}"
    echo "API_ID=your_api_id"
    echo "API_HASH=your_api_hash"
    echo "BOT_TOKEN=your_bot_token"
    echo "MONGO_URI=mongodb://localhost:27017"
    echo "OWNER_ID=your_telegram_id"
    exit 1
fi

# Load environment variables
source .env

# Check for required tools
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 found${NC}"

# Check Docker (optional)
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    DOCKER_AVAILABLE=true
    echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
else
    DOCKER_AVAILABLE=false
    echo -e "${YELLOW}⚠️  Docker not found. Will use local installation.${NC}"
fi

# Create necessary directories
mkdir -p sessions logs

# Setup based on deployment method
if [ "$1" == "docker" ] || [ "$DOCKER_AVAILABLE" == true ] && [ "$1" != "local" ]; then
    echo -e "${GREEN}🐳 Deploying with Docker...${NC}"
    
    # Build and start containers
    docker-compose down
    docker-compose up --build -d
    
    # Check if running
    sleep 5
    if docker ps | grep -q "telegram_report_bot"; then
        echo -e "${GREEN}✅ Bot running in Docker container${NC}"
        echo -e "${YELLOW}📋 To view logs: docker-compose logs -f${NC}"
    else
        echo -e "${RED}❌ Bot failed to start. Check logs: docker-compose logs${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}🐍 Deploying locally...${NC}"
    
    # Install Python dependencies
    echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
    pip3 install -r requirements.txt || pip install -r requirements.txt
    
    # Setup database
    echo -e "${YELLOW}🗄️ Setting up database...${NC}"
    python3 setup_db.py
    
    # Start bot
    echo -e "${GREEN}🤖 Starting bot...${NC}"
    
    # Check if running with PM2
    if command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}📌 Starting with PM2...${NC}"
        pm2 start main.py --name telegram-bot --interpreter python3
        pm2 save
        echo -e "${GREEN}✅ Bot started with PM2${NC}"
        echo -e "${YELLOW}📋 To view logs: pm2 logs telegram-bot${NC}"
    else
        echo -e "${YELLOW}⚠️  PM2 not found. Running directly...${NC}"
        echo -e "${YELLOW}💡 Install PM2: npm install -g pm2${NC}"
        python3 main.py
    fi
fi

echo -e "${GREEN}✅ Deployment complete!${NC}"