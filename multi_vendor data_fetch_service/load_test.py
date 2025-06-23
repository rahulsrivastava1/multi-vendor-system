#!/usr/bin/env python3
"""
Load Testing Script for Multi-Vendor Data Fetch Service

This script uses k6 to perform load testing with:
- 200 concurrent users
- 60 seconds duration
- Mix of POST and GET requests
"""

import json
import subprocess
import time
from typing import Any, Dict, List

import requests

# Configuration
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 200
TEST_DURATION = "60s"


def create_k6_script() -> str:
    """Create the k6 test script"""
    return """
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '10s', target: 50 },   // Ramp up to 50 users
    { duration: '10s', target: 200 },  // Ramp up to 200 users
    { duration: '30s', target: 200 },  // Stay at 200 users
    { duration: '10s', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    http_req_failed: ['rate<0.1'],     // Error rate should be below 10%
    errors: ['rate<0.1'],
  },
};

// Test data
const testPayloads = [
  { "field1": "test1", "field2": 100, "field3": "data1" },
  { "field1": "test2", "field2": 200, "field3": "data2" },
  { "field1": "test3", "field2": 300, "field3": "data3" },
  { "field1": "test4", "field2": 400, "field3": "data4" },
  { "field1": "test5", "field2": 500, "field3": "data5" },
];

// Shared state
let jobIds = [];

export default function() {
  const baseUrl = 'http://localhost:8000';
  
  // Random sleep between requests
  sleep(Math.random() * 2);
  
  // 70% POST requests (create jobs)
  if (Math.random() < 0.7) {
    const payload = testPayloads[Math.floor(Math.random() * testPayloads.length)];
    
    const createResponse = http.post(`${baseUrl}/jobs`, JSON.stringify(payload), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    check(createResponse, {
      'create job status is 200': (r) => r.status === 200,
      'create job has request_id': (r) => r.json('request_id') !== undefined,
    });
    
    if (createResponse.status === 200) {
      const requestId = createResponse.json('request_id');
      jobIds.push(requestId);
      
      // Keep only last 100 job IDs to avoid memory issues
      if (jobIds.length > 100) {
        jobIds = jobIds.slice(-100);
      }
    }
    
    if (createResponse.status !== 200) {
      errorRate.add(1);
    }
  }
  
  // 30% GET requests (check job status)
  else {
    if (jobIds.length > 0) {
      const randomJobId = jobIds[Math.floor(Math.random() * jobIds.length)];
      
      const statusResponse = http.get(`${baseUrl}/jobs/${randomJobId}`);
      
      check(statusResponse, {
        'get job status is 200 or 404': (r) => r.status === 200 || r.status === 404,
        'get job has status field': (r) => r.status === 404 || r.json('status') !== undefined,
      });
      
      if (statusResponse.status !== 200 && statusResponse.status !== 404) {
        errorRate.add(1);
      }
    }
  }
  
  // Health check (occasionally)
  if (Math.random() < 0.1) {
    const healthResponse = http.get(`${baseUrl}/health`);
    
    check(healthResponse, {
      'health check status is 200': (r) => r.status === 200,
      'health check has status field': (r) => r.json('status') === 'healthy',
    });
  }
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const { metrics, root_group } = data;
  const { http_req_duration, http_req_failed, http_reqs } = metrics;
  
  return `
Load Test Results
=================

Test Configuration:
- Concurrent Users: ${CONCURRENT_USERS}
- Duration: ${TEST_DURATION}
- Base URL: ${BASE_URL}

HTTP Metrics:
- Total Requests: ${http_reqs.count}
- Failed Requests: ${http_req_failed.rate * 100:.2f}%
- Average Response Time: ${http_req_duration.avg:.2f}ms
- 95th Percentile: ${http_req_duration.values['p(95)']:.2f}ms
- 99th Percentile: ${http_req_duration.values['p(99)']:.2f}ms

Error Rate: ${errorRate.rate * 100:.2f}%
  `;
}
"""


def run_k6_test() -> Dict[str, Any]:
    """Run the k6 load test"""
    print("Starting k6 load test...")
    print(f"Configuration: {CONCURRENT_USERS} concurrent users for {TEST_DURATION}")
    print(f"Target: {BASE_URL}")
    print("-" * 50)

    # Create k6 script file
    script_content = create_k6_script()
    with open("load_test.js", "w") as f:
        f.write(script_content)

    try:
        # Run k6 test
        result = subprocess.run(
            ["k6", "run", "--out", "json=results.json", "--summary-export", "summary.json", "load_test.js"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        print("k6 Output:")
        print(result.stdout)

        if result.stderr:
            print("k6 Errors:")
            print(result.stderr)

        # Parse results
        try:
            with open("summary.json", "r") as f:
                summary = json.load(f)
            return summary
        except FileNotFoundError:
            print("Warning: Could not find summary.json")
            return {}

    except subprocess.TimeoutExpired:
        print("k6 test timed out")
        return {}
    except FileNotFoundError:
        print("Error: k6 not found. Please install k6 first.")
        print("Installation: https://k6.io/docs/getting-started/installation/")
        return {}


def analyze_results(summary: Dict[str, Any]) -> None:
    """Analyze and print test results"""
    print("\n" + "=" * 60)
    print("LOAD TEST ANALYSIS")
    print("=" * 60)

    if not summary:
        print("No results to analyze")
        return

    metrics = summary.get("metrics", {})

    # Extract key metrics
    http_reqs = metrics.get("http_reqs", {})
    http_req_duration = metrics.get("http_req_duration", {})
    http_req_failed = metrics.get("http_req_failed", {})

    print(f"Total Requests: {http_reqs.get('count', 'N/A')}")
    print(f"Failed Requests: {http_req_failed.get('rate', 0) * 100:.2f}%")
    print(f"Average Response Time: {http_req_duration.get('avg', 0):.2f}ms")
    print(f"95th Percentile: {http_req_duration.get('values', {}).get('p(95)', 0):.2f}ms")
    print(f"99th Percentile: {http_req_duration.get('values', {}).get('p(99)', 0):.2f}ms")

    # Performance insights
    print("\nPERFORMANCE INSIGHTS:")
    print("-" * 30)

    avg_response_time = http_req_duration.get("avg", 0)
    if avg_response_time < 500:
        print("✓ Excellent response times (< 500ms)")
    elif avg_response_time < 1000:
        print("✓ Good response times (< 1s)")
    elif avg_response_time < 2000:
        print("⚠ Acceptable response times (< 2s)")
    else:
        print("✗ Slow response times (> 2s) - needs optimization")

    error_rate = http_req_failed.get("rate", 0) * 100
    if error_rate < 1:
        print("✓ Excellent error rate (< 1%)")
    elif error_rate < 5:
        print("✓ Good error rate (< 5%)")
    elif error_rate < 10:
        print("⚠ Acceptable error rate (< 10%)")
    else:
        print("✗ High error rate (> 10%) - needs investigation")

    # Recommendations
    print("\nRECOMMENDATIONS:")
    print("-" * 20)

    if avg_response_time > 1000:
        print("• Consider optimizing database queries")
        print("• Review vendor rate limiting implementation")
        print("• Add caching for frequently accessed data")

    if error_rate > 5:
        print("• Investigate failed requests in logs")
        print("• Check vendor service availability")
        print("• Review error handling in worker tasks")

    print("• Monitor MongoDB connection pool")
    print("• Consider horizontal scaling for workers")
    print("• Implement circuit breakers for vendor calls")


def check_service_health() -> bool:
    """Check if the service is running and healthy"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Service is healthy")
            return True
        else:
            print(f"✗ Service returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to service: {e}")
        return False


def main():
    """Main function"""
    print("Multi-Vendor Data Fetch Service - Load Test")
    print("=" * 50)

    # Check if service is running
    if not check_service_health():
        print("\nPlease start the service first:")
        print("docker-compose up -d")
        return

    # Run load test
    summary = run_k6_test()

    # Analyze results
    analyze_results(summary)

    # Cleanup
    try:
        import os

        os.remove("load_test.js")
        os.remove("results.json")
        os.remove("summary.json")
    except:
        pass


if __name__ == "__main__":
    main()
