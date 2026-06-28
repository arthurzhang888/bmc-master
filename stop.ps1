# BMC Master Stop Script for Windows (PowerShell)

Write-Host "Stopping BMC Master services..."

# Stop Celery worker
if (Test-Path "logs/celery-worker.pid") {
    $workerPid = Get-Content logs/celery-worker.pid
    Stop-Job -Id $workerPid -ErrorAction SilentlyContinue
    Remove-Item logs/celery-worker.pid
}

# Stop Celery beat
if (Test-Path "logs/celery-beat.pid") {
    $beatPid = Get-Content logs/celery-beat.pid
    Stop-Job -Id $beatPid -ErrorAction SilentlyContinue
    Remove-Item logs/celery-beat.pid
}

# Stop Docker if running in Docker mode
if ($args[0] -eq "docker") {
    docker-compose down
}

Write-Host "BMC Master stopped."