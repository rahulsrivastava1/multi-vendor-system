import os
from typing import Optional


class Settings:
    # Database
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    MONGODB_DB: str = "vendor_service"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Vendor URLs
    VENDOR_SYNC_URL: str = os.getenv("VENDOR_SYNC_URL", "http://localhost:8001")
    VENDOR_ASYNC_URL: str = os.getenv("VENDOR_ASYNC_URL", "http://localhost:8002")

    # Rate limiting
    SYNC_VENDOR_RATE_LIMIT: int = 30  # requests per minute
    ASYNC_VENDOR_RATE_LIMIT: int = 20  # requests per minute

    # Application
    APP_NAME: str = "Multi-Vendor Data Fetch Service"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings()
