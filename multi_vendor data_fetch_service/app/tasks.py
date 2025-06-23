import asyncio
import logging
import random
import time

import httpx
from celery import current_task

from app.celery_app import celery_app
from app.config import settings
from app.database import db_manager
from app.models import JobStatus, VendorType
from app.vendor_client import VendorClient

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis for this)
rate_limit_storage = {
    "sync": {"last_request": 0, "requests_this_minute": 0},
    "async": {"last_request": 0, "requests_this_minute": 0},
}


def check_rate_limit(vendor_type: str, rate_limit: int) -> bool:
    """Check if we can make a request to the vendor"""
    current_time = time.time()
    minute_ago = current_time - 60

    # Reset counter if a minute has passed
    if rate_limit_storage[vendor_type]["last_request"] < minute_ago:
        rate_limit_storage[vendor_type]["requests_this_minute"] = 0

    # Check if we're under the limit
    if rate_limit_storage[vendor_type]["requests_this_minute"] >= rate_limit:
        return False

    return True


def update_rate_limit(vendor_type: str):
    """Update rate limit counters"""
    current_time = int(time.time())
    rate_limit_storage[vendor_type]["last_request"] = current_time
    rate_limit_storage[vendor_type]["requests_this_minute"] += 1


def clean_vendor_response(data: dict) -> dict:
    """Clean vendor response by trimming strings and removing PII"""
    cleaned_data = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Trim strings and remove potential PII
            cleaned_value = value.strip()
            if any(pii in key.lower() for pii in ["email", "phone", "ssn", "password"]):
                cleaned_value = "[REDACTED]"
            cleaned_data[key] = cleaned_value
        elif isinstance(value, dict):
            cleaned_data[key] = clean_vendor_response(value)
        elif isinstance(value, list):
            cleaned_data[key] = [clean_vendor_response(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned_data[key] = value

    return cleaned_data


@celery_app.task(bind=True)
def process_job(self, request_id: str, payload: dict):
    """Process a job by calling the appropriate vendor"""
    try:
        logger.info(f"Starting to process job {request_id}")

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Update job status to processing
            loop.run_until_complete(db_manager.update_job(request_id, {"status": JobStatus.PROCESSING}))

            # Randomly choose vendor type (in real scenario, this would be based on payload)
            vendor_type = random.choice([VendorType.SYNC, VendorType.ASYNC])

            # Determine rate limit
            rate_limit = (
                settings.SYNC_VENDOR_RATE_LIMIT if vendor_type == VendorType.SYNC else settings.ASYNC_VENDOR_RATE_LIMIT
            )

            # Check rate limit
            while not check_rate_limit(vendor_type.value, rate_limit):
                logger.info(f"Rate limit reached for {vendor_type} vendor, waiting...")
                time.sleep(2)  # Wait 2 seconds before retrying

            # Update rate limit counter
            update_rate_limit(vendor_type.value)

            # Update job with vendor type
            loop.run_until_complete(db_manager.update_job(request_id, {"vendor_type": vendor_type}))

            # Call vendor
            vendor_client = VendorClient()

            if vendor_type == VendorType.SYNC:
                # Synchronous vendor
                logger.info(f"Calling synchronous vendor for job {request_id}")
                response = loop.run_until_complete(vendor_client.call_sync_vendor(payload))

                # Clean response
                cleaned_response = clean_vendor_response(response)

                # Update job as complete
                loop.run_until_complete(
                    db_manager.update_job(request_id, {"status": JobStatus.COMPLETE, "result": cleaned_response})
                )

                logger.info(f"Job {request_id} completed successfully")

            else:
                # Asynchronous vendor
                logger.info(f"Calling asynchronous vendor for job {request_id}")
                response = loop.run_until_complete(vendor_client.call_async_vendor(payload))

                # Store vendor response ID for webhook
                loop.run_until_complete(
                    db_manager.update_job(
                        request_id,
                        {
                            "vendor_response_id": response.get("response_id"),
                            "status": JobStatus.PROCESSING,  # Keep as processing until webhook
                        },
                    )
                )

                logger.info(f"Job {request_id} submitted to async vendor, waiting for webhook")

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error processing job {request_id}: {e}")

        # Update job as failed
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(db_manager.update_job(request_id, {"status": JobStatus.FAILED, "error": str(e)}))
            loop.close()
        except:
            pass

        # Re-raise for Celery to handle
        raise


@celery_app.task
def handle_vendor_webhook(request_id: str, vendor_data: dict):
    """Handle webhook from async vendor"""
    try:
        logger.info(f"Processing webhook for job {request_id}")

        # Clean vendor response
        cleaned_response = clean_vendor_response(vendor_data)

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Update job as complete
            loop.run_until_complete(
                db_manager.update_job(request_id, {"status": JobStatus.COMPLETE, "result": cleaned_response})
            )

            logger.info(f"Job {request_id} completed via webhook")

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error processing webhook for job {request_id}: {e}")

        # Update job as failed
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(db_manager.update_job(request_id, {"status": JobStatus.FAILED, "error": str(e)}))
            loop.close()
        except:
            pass

        raise
