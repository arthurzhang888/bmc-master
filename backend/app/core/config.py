import os
import platform
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database and Cache
    DATABASE_URL: str = "postgresql+asyncpg://bmc:bmc_secret@localhost:5432/bmc_master"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Project Info
    PROJECT_NAME: str = "BMC Master"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Platform-specific settings
    LOG_LEVEL: str = "INFO"

    # Email settings (optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@bmc-master.local"
    ALERT_EMAIL: str = "admin@example.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Support both Unix and Windows env files
        case_sensitive = False

    @property
    def log_dir(self) -> Path:
        """Get platform-appropriate log directory."""
        if platform.system() == "Windows":
            log_path = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "bmc-master" / "logs"
        else:
            log_path = Path("/var/log/bmc-master")
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path

    @property
    def data_dir(self) -> Path:
        """Get platform-appropriate data directory."""
        if platform.system() == "Windows":
            data_path = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "bmc-master" / "data"
        else:
            data_path = Path("/var/lib/bmc-master")
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @property
    def temp_dir(self) -> Path:
        """Get platform-appropriate temp directory."""
        import tempfile
        temp_path = Path(tempfile.gettempdir()) / "bmc-master"
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
