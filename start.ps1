# BMC Master Startup Script for Windows (PowerShell)

$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Reset = "`e[0m"

Write-Host "$Green Starting BMC Master...$Reset"

# Check if running in Docker mode
if ($args[0] -eq "docker") {
    Write-Host "$Yellow Starting with Docker Compose...$Reset"
    docker-compose up -d
    Write-Host "$Green BMC Master started!$Reset"
    Write-Host "Frontend: http://localhost:3000"
    Write-Host "Backend API: http://localhost:8000"
    Write-Host "API Docs: http://localhost:8000/docs"
    exit 0
}

# Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "$Red Python is not installed$Reset"
    exit 1
}

# Check if virtual environment exists
if (!(Test-Path "backend\venv")) {
    Write-Host "$Yellow Creating virtual environment...$Reset"
    Set-Location backend
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Set-Location ..
} else {
    .\backend\venv\Scripts\Activate.ps1
}

# Check environment file
if (!(Test-Path ".env")) {
    Write-Host "$Yellow Creating .env from example...$Reset"
    Copy-Item .env.example .env
}

# Create logs directory
New-Item -ItemType Directory -Force -Path logs | Out-Null

# Run migrations
Write-Host "$Yellow Running database migrations...$Reset"
Set-Location backend
alembic upgrade head
Set-Location ..

# Start Celery worker in background
Write-Host "$Yellow Starting Celery worker...$Reset"
$workerJob = Start-Job -ScriptBlock {
    Set-Location backend
    .\venv\Scripts\Activate.ps1
    celery -A app.tasks worker --loglevel=info --pool=solo
}

# Start Celery beat in background
Write-Host "$Yellow Starting Celery beat...$Reset"
$beatJob = Start-Job -ScriptBlock {
    Set-Location backend
    .\venv\Scripts\Activate.ps1
    celery -A app.tasks beat --loglevel=info
}

# Save job IDs for later cleanup
$workerJob.Id | Out-File -FilePath logs/celery-worker.pid
$beatJob.Id | Out-File -FilePath logs/celery-beat.pid

# Start backend
Write-Host "$Green Starting backend server...$Reset"
Set-Location backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload