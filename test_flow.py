#!/usr/bin/env python3
"""
Test script for Marketing Video Agent Factory user flow.
Tests the complete user journey from brand setup to video generation.
"""

import requests
import json
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:5002"
SESSION_ID = "test_session_001"

def print_step(step_num, description):
    """Print a formatted test step."""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60)

def test_health():
    """Test health endpoint."""
    print_step(1, "Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_brand_setup():
    """Test brand setup via chat (brand setup is sent through chat interface)."""
    print_step(2, "Testing Brand Setup via Chat")
    try:
        # Brand setup is sent through chat, not a separate endpoint
        # The frontend sends brand info as a chat message with attachments
        brand_message = """Brand information:
- Company: TechStart Inc
- Industry: Technology
- Tone: Professional
- Company Overview: TechStart Inc is a leading provider of AI-powered solutions for businesses.
- TARGET AUDIENCE: Small to medium enterprises looking to automate workflows
- PRODUCTS/SERVICES: AI automation platform, workflow management tools, analytics dashboard
- MARKETING_GOALS: brand_awareness, lead_generation, product_launch
- BRAND_MESSAGING: Empower your business with intelligent automation
- COMPETITIVE_POSITIONING: Most user-friendly AI platform with fastest implementation time
- KEY_DIFFERENTIATORS: No-code setup, 24/7 support, Enterprise-grade security"""
        
        chat_data = {
            "session_id": SESSION_ID,
            "message": brand_message,
            "last_generated_video": ""
        }
        
        print("Sending brand setup message through chat...")
        response = requests.post(
            f"{BASE_URL}/chat/stream",
            json=chat_data,
            stream=True,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            chunks = []
            for i, chunk in enumerate(response.iter_content(chunk_size=1024, decode_unicode=True)):
                if chunk:
                    chunks.append(chunk)
                if i >= 5:  # Limit chunks for testing
                    break
            print(f"✅ Received {len(chunks)} response chunks")
            print("✅ Brand setup via chat passed")
            return True
        else:
            print(f"❌ Brand setup failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Brand setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_marketing_context():
    """Test marketing context upload."""
    print_step(3, "Testing Marketing Context Upload")
    try:
        marketing_data = {
            "session_id": SESSION_ID,
            "company_overview": "TechStart Inc is a leading provider of AI-powered solutions for businesses.",
            "target_audience": "Small to medium enterprises looking to automate workflows",
            "products_services": "AI automation platform, workflow management tools, analytics dashboard",
            "marketing_goals": ["brand_awareness", "lead_generation", "product_launch"],
            "brand_messaging": "Empower your business with intelligent automation",
            "competitive_positioning": "Most user-friendly AI platform with fastest implementation time",
            "key_differentiators": ["No-code setup", "24/7 support", "Enterprise-grade security"]
        }
        response = requests.post(
            f"{BASE_URL}/upload-marketing-context",
            json=marketing_data,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
        print("✅ Marketing context upload passed")
        return True
    except Exception as e:
        print(f"❌ Marketing context upload failed: {e}")
        return False

def test_chat_initial():
    """Test initial chat message."""
    print_step(4, "Testing Initial Chat Message")
    try:
        chat_data = {
            "session_id": SESSION_ID,
            "message": "Hello! I'd like to create a brand story video for TechStart Inc.",
            "last_generated_video": ""
        }
        print(f"Sending: {chat_data['message']}")
        print("(This will stream responses - showing first chunk only)")
        
        response = requests.post(
            f"{BASE_URL}/chat/stream",
            json=chat_data,
            stream=True,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            # Read first few chunks
            chunks = []
            for i, chunk in enumerate(response.iter_content(chunk_size=1024, decode_unicode=True)):
                if chunk:
                    chunks.append(chunk)
                    if i < 3:  # Show first 3 chunks
                        print(f"Chunk {i+1}: {chunk[:200]}...")
                if i >= 10:  # Limit to first 10 chunks for testing
                    break
            print(f"✅ Received {len(chunks)} response chunks")
            return True
        else:
            print(f"❌ Chat failed with status {response.status_code}")
            print(response.text[:500])
            return False
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_generated_videos():
    """Test generated videos endpoint."""
    print_step(5, "Testing Generated Videos Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/generated-videos?session_id={SESSION_ID}",
            timeout=5
        )
        print(f"Status: {response.status_code}")
        videos = response.json()
        print(f"Response: {json.dumps(videos, indent=2)}")
        assert response.status_code == 200
        assert "videos" in videos
        print(f"✅ Found {len(videos.get('videos', []))} generated videos")
        return True
    except Exception as e:
        print(f"❌ Generated videos check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MARKETING VIDEO AGENT FACTORY - USER FLOW TEST")
    print("="*60)
    
    # Check if server is running
    if not test_health():
        print("\n❌ Server is not running or health check failed!")
        print("Please start the server first:")
        print("  cd /home/pankaj/POC/marketing_video_agent_factory")
        print("  source venv/bin/activate")
        print("  python3 -m app.fast_api_app")
        sys.exit(1)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Brand Setup", test_brand_setup()))
    results.append(("Marketing Context", test_marketing_context()))
    results.append(("Chat Initial", test_chat_initial()))
    results.append(("Generated Videos", test_generated_videos()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The application is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
