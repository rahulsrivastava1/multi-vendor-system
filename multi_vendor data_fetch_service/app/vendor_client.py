import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VendorClient:
    def __init__(self):
        self.sync_url = settings.VENDOR_SYNC_URL
        self.async_url = settings.VENDOR_ASYNC_URL
        self.timeout = httpx.Timeout(30.0)

    async def call_sync_vendor(self, payload: dict) -> dict:
        """Call the synchronous vendor"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.sync_url}/process", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error calling sync vendor: {e}")
            raise

    async def call_async_vendor(self, payload: dict) -> dict:
        """Call the asynchronous vendor"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.async_url}/submit", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error calling async vendor: {e}")
            raise
