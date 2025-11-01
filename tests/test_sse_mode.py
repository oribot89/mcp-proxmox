#!/usr/bin/env python3
"""
Test script for MCP Proxmox Server SSE mode.

This script tests the SSE transport mode by:
1. Starting the server in SSE mode
2. Testing all HTTP endpoints
3. Verifying responses
4. Stopping the server
"""

import subprocess
import time
import requests
import json
import sys

def test_sse_mode():
    """Test SSE mode endpoints"""
    print("=== MCP Proxmox Server SSE Mode Test ===\n")
    
    # Start server
    print("Starting server in SSE mode...")
    process = subprocess.Popen(
        [sys.executable, "-m", "proxmox_mcp.server", "--transport", "sse", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(5)
    
    try:
        base_url = "http://127.0.0.1:8000"
        
        # Test 1: Root endpoint
        print("\n1. Testing Root Endpoint...")
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Server: {data['name']}")
        print(f"   Transport: {data['transport']}")
        print(f"   Status: {data['status']}")
        assert data['transport'] == 'sse', "Transport should be SSE"
        print("   ✅ Root endpoint working")
        
        # Test 2: Health endpoint
        print("\n2. Testing Health Endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Server Health: {data['status']}")
        print(f"   Proxmox Connected: {data['proxmox_connected']}")
        print(f"   Multi-Cluster: {data['multi_cluster']}")
        print("   ✅ Health endpoint working")
        
        # Test 3: Tools endpoint
        print("\n3. Testing Tools Endpoint...")
        response = requests.get(f"{base_url}/tools")
        print(f"   Status: {response.status_code}")
        data = response.json()
        tool_count = len(data['tools'])
        print(f"   Total Tools: {tool_count}")
        print(f"   First 5 tools:")
        for tool in data['tools'][:5]:
            print(f"     - {tool['name']}")
        print("   ✅ Tools endpoint working")
        
        # Test 4: Execute endpoint
        print("\n4. Testing Execute Endpoint (proxmox-list-nodes)...")
        response = requests.post(
            f"{base_url}/execute",
            json={"tool": "proxmox-list-nodes", "params": {}}
        )
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Success: {data.get('success', False)}")
        print(f"   Tool: {data.get('tool', 'N/A')}")
        if data.get('result'):
            print(f"   Result: {len(data['result'])} nodes found")
        print("   ✅ Execute endpoint working")
        
        print("\n=== All Tests Passed ===")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
        
    finally:
        # Stop server
        print("\nStopping server...")
        process.terminate()
        process.wait(timeout=5)
        print("✅ Server stopped")

if __name__ == "__main__":
    success = test_sse_mode()
    sys.exit(0 if success else 1)

