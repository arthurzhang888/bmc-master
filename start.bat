@echo off
REM BMC Master Startup Script for Windows (Command Prompt)

echo Starting BMC Master...

REM Check if running in Docker mode
if "%1"=="docker" (
    echo Starting with Docker Compose...
    docker-compose up -d
    echo BMC Master started!
    echo Frontend: http://localhost:3000
    echo Backend API: http://localhost:8000
    echo API Docs: http://localhost:8000/docs
    exit /b 0
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed
    exit /b 1
)

REM Check if virtual environment exists
if not exist "backend\venv" (
    echo Creating virtual environment...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
) else (
    call backend\venv\Scripts\activate.bat
)

REM Check environment file
if not exist ".env" (
    echo Creating .env from example...
    copy .env.example .env
)

REM Create logs directory
if not exist logs mkdir logs

REM Run migrations
echo Running database migrations...
cd backend
alembic upgrade head
cd ..

REM Start Celery worker in background
echo Starting Celery worker...
start /B cmd /c "cd backend && call venv\Scripts\activate.bat && celery -A app.tasks worker --loglevel=info --pool=solo > ..\logs\celery-worker.log 2>&1"

REM Start Celery beat in background
echo Starting Celery beat...
start /B cmd /c "cd backend && call venv\Scripts\activate.bat && celery -A app.tasks beat --loglevel=info > ..\logs\celery-beat.log 2>&1"

REM Start backend
echo Starting backend server...
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload