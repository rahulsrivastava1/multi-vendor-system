import logging
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import settings
from app.models import JobDocument

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.jobs_collection: Optional[Collection] = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB]
            self.jobs_collection = self.db.jobs

            # Create indexes
            self.jobs_collection.create_index("request_id", unique=True)
            self.jobs_collection.create_index("status")
            self.jobs_collection.create_index("created_at")

            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def create_job(self, job: JobDocument) -> JobDocument:
        """Create a new job in the database"""
        try:
            job_dict = job.dict()
            self.jobs_collection.insert_one(job_dict)
            return job
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    async def get_job(self, request_id: str) -> Optional[JobDocument]:
        """Get a job by request_id"""
        try:
            job_dict = self.jobs_collection.find_one({"request_id": request_id})
            if job_dict:
                return JobDocument(**job_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get job {request_id}: {e}")
            raise

    async def update_job(self, request_id: str, update_data: dict) -> bool:
        """Update a job in the database"""
        try:
            update_data["updated_at"] = JobDocument().updated_at
            result = self.jobs_collection.update_one({"request_id": request_id}, {"$set": update_data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update job {request_id}: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()
