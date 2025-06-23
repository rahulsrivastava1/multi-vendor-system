import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class VendorType(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


class JobRequest(BaseModel):
    payload: Dict[str, Any] = Field(..., description="Any JSON payload for the job")


class JobResponse(BaseModel):
    request_id: str = Field(..., description="Unique identifier for the job")


class JobStatusResponse(BaseModel):
    request_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VendorWebhookRequest(BaseModel):
    data: Dict[str, Any] = Field(..., description="Vendor response data")
    vendor_id: Optional[str] = None


class JobDocument(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    vendor_type: Optional[VendorType] = None
    vendor_response_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
