#!/bin/bash

# Multi-Vendor Data Fetch Service - cURL Commands
# Make sure the service is running: docker-compose up -d

BASE_URL="http://localhost:8000"

echo "Multi-Vendor Data Fetch Service - API Testing"
echo "=============================================="

# Test 1: Health Check
echo -e "\n1. Health Check"
echo "----------------"
curl -X GET "${BASE_URL}/health" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"

# Test 2: Create Job
echo -e "\n2. Create Job"
echo "-------------"
CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "field1": "test_data",
      "field2": 123,
      "field3": "sample_data"
    }
  }' \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n")

echo "$CREATE_RESPONSE"

# Extract request_id from response
REQUEST_ID=$(echo "$CREATE_RESPONSE" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$REQUEST_ID" ]; then
  echo "Request ID: $REQUEST_ID"
  
  # Test 3: Get Job Status (immediate)
  echo -e "\n3. Get Job Status (immediate)"
  echo "-----------------------------"
  curl -X GET "${BASE_URL}/jobs/${REQUEST_ID}" \
    -H "Content-Type: application/json" \
    -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"
  
  # Wait a bit for processing
  echo -e "\nWaiting 3 seconds for processing..."
  sleep 3
  
  # Test 4: Get Job Status (after processing)
  echo -e "\n4. Get Job Status (after processing)"
  echo "-------------------------------------"
  curl -X GET "${BASE_URL}/jobs/${REQUEST_ID}" \
    -H "Content-Type: application/json" \
    -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"
  
  # Test 5: Vendor Webhook
  echo -e "\n5. Vendor Webhook"
  echo "-----------------"
  curl -X POST "${BASE_URL}/vendor-webhook/test" \
    -H "Content-Type: application/json" \
    -d "{
      \"response_id\": \"${REQUEST_ID}\",
      \"data\": {
        \"vendor_id\": \"test_vendor_001\",
        \"status\": \"success\",
        \"result\": {
          \"processed\": true,
          \"data\": {
            \"field1\": \"webhook_processed\",
            \"field2\": 246,
            \"field3\": \"webhook_enhanced\"
          }
        }
      }
    }" \
    -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"
  
  # Wait for webhook processing
  echo -e "\nWaiting 2 seconds for webhook processing..."
  sleep 2
  
  # Test 6: Get Job Status (after webhook)
  echo -e "\n6. Get Job Status (after webhook)"
  echo "--------------------------------"
  curl -X GET "${BASE_URL}/jobs/${REQUEST_ID}" \
    -H "Content-Type: application/json" \
    -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"
else
  echo "Failed to extract request_id from response"
fi

# Test 7: Get Non-existent Job
echo -e "\n7. Get Non-existent Job"
echo "------------------------"
curl -X GET "${BASE_URL}/jobs/non-existent-id" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"

# Test 8: Metrics Endpoint
echo -e "\n8. Prometheus Metrics"
echo "---------------------"
curl -X GET "${BASE_URL}/metrics" \
  -H "Content-Type: text/plain" \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" | head -20

echo -e "\n=============================================="
echo "API Testing Complete!"
echo "==============================================" 