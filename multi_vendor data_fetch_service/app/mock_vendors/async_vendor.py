import asyncio
import json
import logging
import os
import random
import time
import uuid
from typing import Any, Dict

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Asynchronous Vendor")

# Rate limiting storage
rate_limit_storage = {"last_request": 0, "requests_this_minute": 0}

# Store pending requests
pending_requests = {}


class SubmitRequest(BaseModel):
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


async def process_request_async(response_id: str, data: Dict[str, Any]):
    """Process request asynchronously and send webhook"""
    try:
        # Simulate processing time (2-5 seconds)
        processing_time = random.uniform(2, 5)
        await asyncio.sleep(processing_time)

        # Generate mock response
        response_data = {
            "response_id": response_id,
            "vendor_id": "async_vendor_001",
            "processed_at": time.time(),
            "status": "success",
            "result": {
                "data": data,
                "processed_data": {
                    "field1": f"async_processed_{data.get('field1', 'default')}",
                    "field2": data.get("field2", 0) * 3,
                    "field3": f"async_enhanced_{random.randint(1000, 9999)}",
                    "async_field": f"async_specific_{random.randint(100, 999)}",
                },
                "metadata": {
                    "processing_time_ms": int(processing_time * 1000),
                    "confidence_score": random.uniform(0.7, 0.95),
                    "vendor_version": "2.1.0",
                    "async_processing": True,
                },
            },
        }

        # Send webhook to main service
        webhook_url = "http://api:8000/vendor-webhook/async"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                webhook_response = await client.post(
                    webhook_url, json={"response_id": response_id, "data": response_data}
                )
                webhook_response.raise_for_status()
                logger.info(f"Webhook sent successfully for response_id: {response_id}")
        except Exception as e:
            logger.error(f"Failed to send webhook for response_id {response_id}: {e}")

        # Remove from pending requests
        if response_id in pending_requests:
            del pending_requests[response_id]

    except Exception as e:
        logger.error(f"Error processing async request {response_id}: {e}")


@app.get("/")
async def root():
    return {"message": "Mock Asynchronous Vendor", "status": "running"}


@app.post("/submit")
async def submit_request(request: SubmitRequest, background_tasks: BackgroundTasks):
    """Submit a request for asynchronous processing"""
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

    # Check rate limit
    if not check_rate_limit(rate_limit):
        logger.warning("Rate limit exceeded")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Update rate limit counter
    update_rate_limit()

    # Generate response ID
    response_id = str(uuid.uuid4())

    # Store request for processing
    pending_requests[response_id] = {"data": request.data, "submitted_at": time.time()}

    # Start background processing
    background_tasks.add_task(process_request_async, response_id, request.data)

    logger.info(f"Request submitted for async processing, response_id: {response_id}")

    return {
        "response_id": response_id,
        "status": "accepted",
        "message": "Request submitted for processing",
        "estimated_processing_time": "2-5 seconds",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "vendor_type": "asynchronous", "pending_requests": len(pending_requests)}


@app.get("/pending")
async def get_pending_requests():
    """Get list of pending requests (for debugging)"""
    return {"pending_count": len(pending_requests), "pending_requests": list(pending_requests.keys())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
