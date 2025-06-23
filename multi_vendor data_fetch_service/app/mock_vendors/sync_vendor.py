import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Synchronous Vendor")

# Rate limiting storage
rate_limit_storage = {"last_request": 0, "requests_this_minute": 0}


class ProcessRequest(BaseModel):
    data: Dict[str, Any]


def check_rate_limit(rate_limit: int) -> bool:
    """Check if we can process a request"""
    current_time = time.time()
    minute_ago = current_time - 60

    # Reset counter if a minute has passed
    if rate_limit_storage["last_request"] < minute_ago:
        rate_limit_storage["requests_this_minute"] = 0

    # Check if we're under the limit
    if rate_limit_storage["requests_this_minute"] >= rate_limit:
        return False

    return True


def update_rate_limit():
    """Update rate limit counters"""
    current_time = int(time.time())
    rate_limit_storage["last_request"] = current_time
    rate_limit_storage["requests_this_minute"] += 1


@app.get("/")
async def root():
    return {"message": "Mock Synchronous Vendor", "status": "running"}


@app.post("/process")
async def process_request(request: ProcessRequest):
    """Process a request synchronously"""
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # Check rate limit
    if not check_rate_limit(rate_limit):
        logger.warning("Rate limit exceeded")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Update rate limit counter
    update_rate_limit()

    # Simulate processing time
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Generate mock response
    response_data = {
        "vendor_id": "sync_vendor_001",
        "processed_at": time.time(),
        "status": "success",
        "result": {
            "data": request.data,
            "processed_data": {
                "field1": f"processed_{request.data.get('field1', 'default')}",
                "field2": request.data.get("field2", 0) * 2,
                "field3": f"vendor_enhanced_{random.randint(1000, 9999)}",
            },
            "metadata": {
                "processing_time_ms": random.randint(50, 200),
                "confidence_score": random.uniform(0.8, 1.0),
                "vendor_version": "1.2.3",
            },
        },
    }

    logger.info(f"Processed request successfully")
    return response_data


@app.get("/health")
async def health_check():
    return {"status": "healthy", "vendor_type": "synchronous"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
