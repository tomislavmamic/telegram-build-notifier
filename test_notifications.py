#!/usr/bin/env python3
"""
Test script for verifying both build and invoice notification functions.
"""

import json
import base64
from unittest.mock import Mock
from main import build_notifier, invoice_notifier, unified_notifier

def test_build_notification():
    """Test build notification function with sample data."""
    
    # Sample build event data
    build_data = {
        "status": "SUCCESS",
        "projectId": "test-project",
        "id": "build-123",
        "substitutions": {
            "REPO_NAME": "test-repo",
            "BRANCH_NAME": "main"
        }
    }
    
    # Create cloud event
    cloud_event = {
        "data": base64.b64encode(json.dumps(build_data).encode('utf-8')).decode('utf-8')
    }
    
    context = Mock()
    
    print("Testing build notification...")
    try:
        build_notifier(cloud_event, context)
        print("✅ Build notification test passed")
    except Exception as e:
        print(f"❌ Build notification test failed: {e}")

def test_invoice_notification():
    """Test invoice notification function with sample data."""
    
    # Sample invoice event data
    invoice_data = {
        "event_type": "invoice_creation",
        "status": "success",
        "invoice_id": "invoice-456",
        "external_order_id": "order-789",
        "customer_name": "Test Customer",
        "amount": 99.99,
        "currency": "EUR"
    }
    
    # Create cloud event
    cloud_event = {
        "data": base64.b64encode(json.dumps(invoice_data).encode('utf-8')).decode('utf-8')
    }
    
    context = Mock()
    
    print("Testing invoice notification...")
    try:
        invoice_notifier(cloud_event, context)
        print("✅ Invoice notification test passed")
    except Exception as e:
        print(f"❌ Invoice notification test failed: {e}")

def test_invoice_failure_notification():
    """Test invoice failure notification."""
    
    # Sample invoice failure event data
    invoice_data = {
        "event_type": "invoice_creation",
        "status": "failure",
        "external_order_id": "order-999",
        "customer_name": "Test Customer",
        "error_message": "Minimax API connection failed"
    }
    
    # Create cloud event
    cloud_event = {
        "data": base64.b64encode(json.dumps(invoice_data).encode('utf-8')).decode('utf-8')
    }
    
    context = Mock()
    
    print("Testing invoice failure notification...")
    try:
        invoice_notifier(cloud_event, context)
        print("✅ Invoice failure notification test passed")
    except Exception as e:
        print(f"❌ Invoice failure notification test failed: {e}")

def test_unified_notification():
    """Test unified notification function with both build and invoice events."""
    
    # Test build event
    build_data = {
        "status": "SUCCESS",
        "projectId": "test-project",
        "id": "build-123",
        "substitutions": {
            "REPO_NAME": "test-repo",
            "BRANCH_NAME": "main"
        }
    }
    
    cloud_event = {
        "data": base64.b64encode(json.dumps(build_data).encode('utf-8')).decode('utf-8')
    }
    
    context = Mock()
    
    print("Testing unified notification with build event...")
    try:
        unified_notifier(cloud_event, context)
        print("✅ Unified notification (build) test passed")
    except Exception as e:
        print(f"❌ Unified notification (build) test failed: {e}")
    
    # Test invoice event
    invoice_data = {
        "event_type": "invoice_creation",
        "status": "success",
        "invoice_id": "invoice-456",
        "external_order_id": "order-789",
        "customer_name": "Test Customer",
        "amount": 99.99,
        "currency": "EUR"
    }
    
    cloud_event = {
        "data": base64.b64encode(json.dumps(invoice_data).encode('utf-8')).decode('utf-8')
    }
    
    print("Testing unified notification with invoice event...")
    try:
        unified_notifier(cloud_event, context)
        print("✅ Unified notification (invoice) test passed")
    except Exception as e:
        print(f"❌ Unified notification (invoice) test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Telegram notification functions...")
    print("Note: These tests will attempt to send actual Telegram messages if BOT_TOKEN and CHAT_ID are set.")
    print("Set these environment variables to test actual message sending.\n")
    
    test_build_notification()
    print()
    test_invoice_notification()
    print()
    test_invoice_failure_notification()
    print()
    test_unified_notification()
    print("\n🎉 All tests completed!")