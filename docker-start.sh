#!/bin/bash

# docker-start.sh
echo "🚀 Starting Telegram Report Bot with Docker..."

# Create necessary directories
mkdir -p sessions logs

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Create .env file with:"
    echo "API_ID=your_api_id"
    echo "API_HASH=your_api_hash"
    echo "BOT_TOKEN=your_bot_token"
    echo "MONGO_URI=mongodb://admin:password@mongodb:27017"
    echo "OWNER_ID=your_telegram_id"
    exit 1
fi

# Load environment variables
source .env

# Check if API_ID is set
if [ -z "$API_ID" ] || [ "$API_ID" == "0" ]; then
    echo "❌ API_ID not set in .env"
    exit 1
fi

# Stop and remove old containers
docker-compose down

# Build and start
docker-compose up --build -d

# Check if running
sleep 5
if docker ps | grep -q "telegram_report_bot"; then
    echo "✅ Bot running in Docker container"
    echo "📋 View logs: docker-compose logs -f telegram-bot"
    echo "📋 View MongoDB logs: docker-compose logs -f mongodb"
else
    echo "❌ Bot failed to start. Check logs: docker-compose logs"
    docker-compose logs
    exit 1
fi