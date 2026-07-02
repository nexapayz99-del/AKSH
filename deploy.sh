# deploy.sh
#!/bin/bash

echo "🚀 Deploying Telegram Report Bot..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Setup MongoDB indexes
echo "🗄️ Setting up MongoDB indexes..."
python3 setup_db.py

# Start bot
echo "🤖 Starting bot..."
python3 main.py
