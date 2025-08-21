#!/usr/bin/env python3
"""
Test script for the monitoring system.
This can be run locally to test the monitoring logic.
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from main import (
    get_database_connection, 
    check_stuck_jobs, 
    check_worker_health, 
    format_stuck_jobs_alert,
    format_worker_health_alert,
    send_telegram_alert
)


def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    try:
        db_session = get_database_connection()
        print("✅ Database connection successful")
        
        # Test a simple query
        result = db_session.execute("SELECT COUNT(*) as count FROM orders")
        total_orders = result.fetchone().count
        print(f"📊 Total orders in database: {total_orders}")
        
        db_session.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_stuck_jobs_check():
    """Test stuck jobs detection."""
    print("\n🔍 Testing stuck jobs detection...")
    try:
        db_session = get_database_connection()
        stuck_jobs = check_stuck_jobs(db_session)
        
        print(f"📋 Found {len(stuck_jobs)} stuck jobs")
        if stuck_jobs:
            print("Stuck jobs details:")
            for job in stuck_jobs[:3]:  # Show first 3
                print(f"  - Order {job['external_order_id']}: {job['hours_stuck']} hours in {job['status']} status")
        
        db_session.close()
        return stuck_jobs
    except Exception as e:
        print(f"❌ Stuck jobs check failed: {e}")
        return []


def test_worker_health():
    """Test worker health check."""
    print("\n🔍 Testing worker health check...")
    try:
        health_status = check_worker_health()
        
        if health_status["healthy"]:
            print(f"✅ Worker is healthy (response time: {health_status['response_time']}s)")
            print(f"   URL: {health_status['url']}")
        else:
            print(f"❌ Worker health check failed: {health_status['error']}")
        
        return health_status
    except Exception as e:
        print(f"❌ Worker health check error: {e}")
        return {"healthy": False, "error": str(e)}


def test_alert_formatting(stuck_jobs, health_status):
    """Test alert message formatting."""
    print("\n🔍 Testing alert formatting...")
    
    # Test stuck jobs alert
    if stuck_jobs:
        stuck_alert = format_stuck_jobs_alert(stuck_jobs)
        if stuck_alert:
            print("📨 Stuck jobs alert preview:")
            print(stuck_alert[:200] + "..." if len(stuck_alert) > 200 else stuck_alert)
    
    # Test worker health alert
    if not health_status["healthy"]:
        health_alert = format_worker_health_alert(health_status)
        if health_alert:
            print("📨 Worker health alert preview:")
            print(health_alert[:200] + "..." if len(health_alert) > 200 else health_alert)


def test_telegram_notification(dry_run=True):
    """Test Telegram notification (dry run by default)."""
    print(f"\n🔍 Testing Telegram notification (dry_run={dry_run})...")
    
    test_message = f"""🧪 <b>MONITORING TEST</b>

This is a test message from the invoicing monitoring system.

⏰ Time: {datetime.utcnow().isoformat()}
🔧 Test run: {dry_run}

If you receive this message, Telegram notifications are working correctly!"""
    
    if dry_run:
        print("📨 Test message (would be sent):")
        print(test_message)
        print("✅ Dry run completed - no message sent")
    else:
        success = send_telegram_alert(test_message)
        if success:
            print("✅ Test message sent successfully to Telegram!")
        else:
            print("❌ Failed to send test message to Telegram")


def main():
    """Run all monitoring tests."""
    print("🚀 Starting monitoring system tests...")
    print("=" * 60)
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection failed - cannot continue tests")
        return
    
    # Test stuck jobs detection
    stuck_jobs = test_stuck_jobs_check()
    
    # Test worker health
    health_status = test_worker_health()
    
    # Test alert formatting
    test_alert_formatting(stuck_jobs, health_status)
    
    # Test Telegram notification (dry run)
    test_telegram_notification(dry_run=True)
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print(f"   • Database: {'✅' if True else '❌'}")
    print(f"   • Stuck jobs: {len(stuck_jobs)} found")
    print(f"   • Worker health: {'✅' if health_status['healthy'] else '❌'}")
    
    # Determine if any alerts would be sent
    would_alert = bool(stuck_jobs or not health_status["healthy"])
    print(f"   • Would send alerts: {'Yes' if would_alert else 'No'}")
    
    if would_alert:
        print("\n⚠️  Issues found - alerts would be sent in production")
    else:
        print("\n✅ No issues found - system appears healthy")
    
    print("\nTo send a real test message to Telegram, run:")
    print("python test_monitoring.py --send-telegram-test")


if __name__ == "__main__":
    if len(sys.argv) > 1 and "--send-telegram-test" in sys.argv:
        test_telegram_notification(dry_run=False)
    else:
        main()