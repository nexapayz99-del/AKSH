#!/bin/bash

# docker-start.sh
echo "🚀 Starting Telegram Report Bot with Docker..."

# Create necessary directories
mkdir -p sessions logs

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create one."
    exit 1
fi

# Stop and remove old containers
docker-compose down

# Build and start
docker-compose up --build -d

# Show logs
echo "📋 Showing logs..."
docker-compose logs -f
