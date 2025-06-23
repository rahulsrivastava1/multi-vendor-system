import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import settings
from app.database import db_manager
from app.models import JobRequest, JobResponse, JobStatusResponse, VendorWebhookRequest
from app.tasks import handle_vendor_webhook, process_job

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Multi-Vendor Data Fetch Service")
    await db_manager.connect()
    logger.info("Connected to database")
    yield
    # Shutdown
    logger.info("Shutting down Multi-Vendor Data Fetch Service")
    await db_manager.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    description="A service that provides a unified API for multiple vendor data fetching",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Record metrics
    REQUEST_DURATION.observe(process_time)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()

    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": settings.APP_NAME, "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time(), "services": {"database": "connected", "redis": "connected"}}


@app.post("/jobs", response_model=JobResponse)
async def create_job(request: JobRequest):
    """
    Create a new job

    Accepts any JSON payload and returns a request_id immediately.
    The job will be processed in the background.
    """
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Create job document
        from app.models import JobDocument

        job = JobDocument(request_id=request_id, payload=request.payload)

        # Save to database
        await db_manager.create_job(job)

        # Queue the job for processing
        process_job.delay(request_id, request.payload)

        logger.info(f"Created job {request_id}")

        return JobResponse(request_id=request_id)

    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create job")


@app.get("/jobs/{request_id}", response_model=JobStatusResponse)
async def get_job_status(request_id: str):
    """
    Get the status of a job

    Returns the current status and result if complete.
    """
    try:
        job = await db_manager.get_job(request_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            request_id=job.request_id,
            status=job.status,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@app.post("/vendor-webhook/{vendor}")
async def vendor_webhook(vendor: str, webhook_data: VendorWebhookRequest):
    """
    Webhook endpoint for vendors to send results

    This endpoint receives results from asynchronous vendors.
    """
    try:
        logger.info(f"Received webhook from vendor {vendor}: {webhook_data}")

        # Extract response_id from webhook data
        response_id = webhook_data.data.get("response_id")
        if not response_id:
            raise HTTPException(status_code=400, detail="Missing response_id in webhook data")

        # Find job by vendor_response_id
        # Note: In a real implementation, you'd want to store a mapping of response_id to request_id
        # For this demo, we'll assume the response_id is the request_id
        request_id = response_id

        # Process the webhook data
        handle_vendor_webhook.delay(request_id, webhook_data.data)

        return {"status": "accepted", "message": "Webhook processed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return JSONResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
