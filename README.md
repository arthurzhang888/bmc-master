# BMC Master

Industrial-grade BMC (Baseboard Management Controller) management system with IPMI/Redfish protocol support.

## Features

- **Multi-Protocol Support**: Redfish (modern) and IPMI (legacy) with auto-detection
- **Real-Time Monitoring**: WebSocket-based sensor data streaming
- **Alert Management**: Configurable threshold-based alerts with email/webhook notifications
- **Event Center**: Centralized event management with acknowledge/resolve workflow
- **SEL Log Collection**: Automatic System Event Log collection from all servers
- **Reporting & Analytics**: Sensor trends, alert statistics, anomaly detection with PDF/Excel/CSV export
- **Bulk Operations**: Power control operations on multiple servers simultaneously
- **Auto Discovery**: Network scanning to discover BMC devices automatically
- **Scheduled Tasks**: Cron-based automation for power control, sensor collection, and SEL log collection
- **NOC-Style UI**: Industrial console aesthetic with dark theme

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   BMC/IPMI  │
│  (React)    │     │  (FastAPI)  │     │  (Redfish)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌─────────┐   ┌─────────┐
              │PostgreSQL│   │  Redis  │
              └─────────┘   └─────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended for all platforms)
- Or: Python 3.9+ and Node.js 18+ (native installation)

### Option 1: Docker Compose (Recommended - All Platforms)

```bash
# Clone and start
git clone <repo-url>
cd bmc-master
docker-compose up -d

# Access the application
# Linux/macOS:
open http://localhost:3000
# Windows:
start http://localhost:3000
```

### Option 2: Native Installation

#### Linux/macOS

```bash
# Start all services
./start.sh

# Or with Docker
./start.sh docker
```

#### Windows

```powershell
# PowerShell
.\start.ps1

# Or Command Prompt
start.bat

# Or with Docker (any shell)
.\start.ps1 docker
```

### Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React web UI |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |

### Platform Support

See [PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md) for detailed platform-specific instructions.

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Servers
- `GET /api/v1/servers` - List all servers
- `POST /api/v1/servers` - Add a new server
- `GET /api/v1/servers/{id}/sensors` - Get server sensor readings
- `GET /api/v1/servers/{id}/sel` - Get server SEL logs

### Events
- `GET /api/v1/events` - List events with filtering
- `POST /api/v1/events/{id}/ack` - Acknowledge/resolve event

### Reports
- `GET /api/v1/reports/sensor-trend` - Sensor trend analysis with statistics
- `GET /api/v1/reports/alert-statistics` - Alert statistics report
- `GET /api/v1/reports/anomalies` - Anomaly detection using Z-score
- `POST /api/v1/reports/export` - Export report to PDF/Excel/CSV

### Bulk Operations
- `POST /api/v1/bulk/power` - Create bulk power control job
- `GET /api/v1/bulk/jobs` - List bulk jobs
- `GET /api/v1/bulk/jobs/{id}` - Get bulk job details

### Auto Discovery
- `POST /api/v1/discovery/scan` - Start network discovery scan
- `GET /api/v1/discovery/jobs` - List discovery jobs
- `GET /api/v1/discovery/jobs/{id}` - Get discovery job details

### Scheduled Tasks
- `POST /api/v1/scheduler/tasks` - Create scheduled task
- `GET /api/v1/scheduler/tasks` - List scheduled tasks
- `PUT /api/v1/scheduler/tasks/{id}` - Update scheduled task
- `DELETE /api/v1/scheduler/tasks/{id}` - Delete scheduled task
- `POST /api/v1/scheduler/tasks/{id}/execute` - Execute task immediately
- `GET /api/v1/scheduler/tasks/{id}/history` - Get task execution history

### WebSocket
- `WS /api/v1/ws/sensors` - WebSocket for real-time sensor data

## Celery Tasks

### Periodic Tasks
- **collect_all_servers_sensors** (30s): Collect sensor data from all servers
- **collect_all_sel_logs** (5min): Collect SEL logs from all servers
- **evaluate_alert_rules** (1min): Evaluate alert rules and trigger notifications
- **check_and_run_due_tasks** (1min): Check and execute scheduled tasks
- **cleanup_old_execution_history** (24h): Clean up old task execution history

### Background Tasks
- **execute_bulk_job_task**: Execute bulk power operations
- **run_discovery_task**: Execute network discovery scan
- **execute_scheduled_task**: Execute a scheduled task

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://bmc:bmc_secret@postgres:5432/bmc_master | Database connection |
| REDIS_URL | redis://redis:6379/0 | Redis connection |
| SECRET_KEY | your-secret-key-change-in-production | JWT secret key |
| SMTP_HOST | - | SMTP server for email alerts |
| SMTP_PORT | 587 | SMTP port |
| SMTP_USER | - | SMTP username |
| SMTP_PASSWORD | - | SMTP password |

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routes
│   │   ├── core/            # Config, database, celery
│   │   ├── models/          # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery background tasks
│   │   └── adapters/        # BMC protocol adapters
│   ├── alembic/             # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── services/        # API clients
│   └── package.json
└── docker-compose.yml
```

## License

MIT
