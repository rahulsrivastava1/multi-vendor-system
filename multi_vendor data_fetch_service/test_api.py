#!/usr/bin/env python3
"""
Simple API Test Script

This script tests the basic functionality of the Multi-Vendor Data Fetch Service.
"""

import json
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_create_job(payload: Dict[str, Any]) -> Optional[str]:
    """Test creating a job"""
    print(f"Creating job with payload: {payload}")
    try:
        response = requests.post(f"{BASE_URL}/jobs", json=payload, headers={"Content-Type": "application/json"})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            return response.json()["request_id"]
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_get_job_status(request_id: str):
    """Test getting job status"""
    print(f"Getting status for job: {request_id}")
    try:
        response = requests.get(f"{BASE_URL}/jobs/{request_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_vendor_webhook(vendor: str, webhook_data: Dict[str, Any]):
    """Test the vendor webhook endpoint"""
    print(f"Testing webhook for vendor: {vendor}")
    try:
        response = requests.post(
            f"{BASE_URL}/vendor-webhook/{vendor}", json=webhook_data, headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests"""
    print("Multi-Vendor Data Fetch Service - API Test")
    print("=" * 50)

    # Test 1: Health check
    print("\n1. Testing Health Check")
    print("-" * 30)
    if not test_health_check():
        print("❌ Health check failed")
        return
    print("✅ Health check passed")

    # Test 2: Create job
    print("\n2. Testing Job Creation")
    print("-" * 30)
    payload = {"field1": "test_data", "field2": 123, "field3": "sample"}
    request_id = test_create_job(payload)
    if not request_id:
        print("❌ Job creation failed")
        return
    print("✅ Job creation passed")

    # Test 3: Check job status (immediately)
    print("\n3. Testing Job Status Check (immediate)")
    print("-" * 30)
    if not test_get_job_status(request_id):
        print("❌ Job status check failed")
        return
    print("✅ Job status check passed")

    # Test 4: Wait and check job status again
    print("\n4. Testing Job Status Check (after 3 seconds)")
    print("-" * 30)
    time.sleep(3)
    if not test_get_job_status(request_id):
        print("❌ Job status check failed")
        return
    print("✅ Job status check passed")

    # Test 5: Test vendor webhook
    print("\n5. Testing Vendor Webhook")
    print("-" * 30)
    webhook_data = {
        "response_id": request_id,
        "data": {"vendor_id": "test_vendor", "status": "success", "result": {"processed": True}},
    }
    if not test_vendor_webhook("test", webhook_data):
        print("❌ Vendor webhook failed")
        return
    print("✅ Vendor webhook passed")

    # Test 6: Check job status after webhook
    print("\n6. Testing Job Status Check (after webhook)")
    print("-" * 30)
    time.sleep(2)
    if not test_get_job_status(request_id):
        print("❌ Job status check failed")
        return
    print("✅ Job status check passed")

    print("\n" + "=" * 50)
    print("🎉 All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
