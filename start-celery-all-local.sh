#!/bin/bash

# Combined Celery worker + beat start script (Local development)
# This script starts both the worker AND the beat scheduler together

echo -e "\033[32mStarting local Celery worker + beat...\033[0m"

# Check if Redis port is available
echo -e "\033[33mChecking Redis...\033[0m"
if nc -z localhost 6379 2>/dev/null; then
    echo -e "\033[32mRedis is already running on port 6379!\033[0m"
else
    echo -e "\033[33mStarting Redis...\033[0m"
    # Remove existing container if it exists
    docker rm -f local-redis 2>/dev/null
    docker run -d --name local-redis -p 6379:6379 redis:alpine
    sleep 3
    echo -e "\033[32mRedis started!\033[0m"
fi

# Load environment variables from .env
echo -e "\033[33mLoading environment variables...\033[0m"
if [ -f ".env" ]; then
    ENV_FILE=".env"
elif [ -f "dev.env" ]; then
    ENV_FILE="dev.env"
else
    ENV_FILE=""
fi

if [ -n "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Start Celery worker with beat scheduler embedded
echo -e "\033[32mStarting Celery worker with Beat scheduler...\033[0m"
echo -e "\033[36mConnecting to Redis: $REDIS_URL\033[0m"

# Start Celery worker with beat embedded (simpler for development)
# -B flag starts beat scheduler in the same process
uv run celery -A src.core.celery worker -B -l info

echo ""
echo -e "\033[32mCelery worker + beat started!\033[0m"
