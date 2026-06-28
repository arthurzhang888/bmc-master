# Platform Support Guide

BMC Master supports both Windows and Linux environments.

## Supported Platforms

### Linux (Recommended)
- Ubuntu 20.04/22.04 LTS
- Debian 11/12
- CentOS 7/8
- Rocky Linux 8/9

### Windows
- Windows 10/11 (Development)
- Windows Server 2019/2022 (Production)

## Running on Linux

### Native Installation
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start Celery worker (in another terminal)
celery -A app.tasks worker --loglevel=info

# Start Celery beat (in another terminal)
celery -A app.tasks beat --loglevel=info
```

### Docker (Recommended)
```bash
docker-compose up -d
```

## Running on Windows

### Option 1: Docker Desktop (Recommended)
Install Docker Desktop for Windows and run:
```powershell
docker-compose up -d
```

### Option 2: Native Installation

#### Prerequisites
- Python 3.9 or higher
- PostgreSQL 14 or higher
- Redis for Windows

#### Setup
```powershell
# Install Python dependencies
pip install -r backend/requirements.txt

# Set environment variables
$env:DATABASE_URL="postgresql+asyncpg://bmc:bmc_secret@localhost:5432/bmc_master"
$env:REDIS_URL="redis://localhost:6379/0"

# Run migrations
cd backend
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start Celery worker (in another PowerShell window)
celery -A app.tasks worker --loglevel=info --pool=solo

# Start Celery beat (in another PowerShell window)
celery -A app.tasks beat --loglevel=info
```

**Note:** On Windows, use `--pool=solo` for Celery worker to avoid fork issues.

### Option 3: WSL2 (Windows Subsystem for Linux)
```powershell
# In WSL2 terminal
sudo apt-get update
sudo apt-get install -y python3-pip postgresql redis-server

# Follow Linux native installation steps
```

## Frontend (All Platforms)

```bash
cd frontend
npm install
npm run dev
```

## Platform-Specific Notes

### Linux
- Logs: `/var/log/bmc-master/`
- Data: `/var/lib/bmc-master/`
- Temp: `/tmp/bmc-master/`

### Windows
- Logs: `%PROGRAMDATA%\bmc-master\logs\`
- Data: `%PROGRAMDATA%\bmc-master\data\`
- Temp: `%TEMP%\bmc-master\`

## Troubleshooting

### Windows-specific Issues

1. **Celery fork error**: Use `--pool=solo` flag
2. **Path issues**: Use forward slashes `/` in config paths
3. **IPMI support**: Install IPMIutil for Windows

### Linux-specific Issues

1. **Permission denied**: Ensure proper permissions on log/data directories
2. **Port binding**: May need `sudo` for ports < 1024

## Development Tips

### VS Code (Cross-platform)
Recommended extensions:
- Python
- ESLint
- Prettier
- Docker

### PyCharm (Cross-platform)
- Set up Run Configurations for backend and Celery
- Configure Python Interpreter for the project

## Production Deployment

For production, use Docker on Linux for best compatibility and performance.

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```