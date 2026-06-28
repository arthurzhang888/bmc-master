#!/bin/bash
# BMC Master Startup Script for Linux/macOS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting BMC Master...${NC}"

# Check if running in Docker mode
if [ "$1" == "docker" ]; then
    echo -e "${YELLOW}Starting with Docker Compose...${NC}"
    docker-compose up -d
    echo -e "${GREEN}BMC Master started!${NC}"
    echo "Frontend: http://localhost:3000"
    echo "Backend API: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    exit 0
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    source backend/venv/bin/activate
fi

# Check environment file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from example...${NC}"
    cp .env.example .env
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
cd backend
alembic upgrade head
cd ..

# Start Celery worker in background
echo -e "${YELLOW}Starting Celery worker...${NC}"
cd backend
nohup celery -A app.tasks worker --loglevel=info > ../logs/celery-worker.log 2>&1 &

# Start Celery beat in background
echo -e "${YELLOW}Starting Celery beat...${NC}"
nohup celery -A app.tasks beat --loglevel=info > ../logs/celery-beat.log 2>&1 &
cd ..

# Create logs directory if not exists
mkdir -p logs

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload