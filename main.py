import json
import requests
import base64
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from google.cloud import functions_v1, secretmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import functions_framework

def build_notifier(cloud_event, context):
    """Cloud Function triggered by Pub/Sub topic for Cloud Build notifications."""
    
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHAT_ID = os.environ.get('CHAT_ID')
    
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing BOT_TOKEN or CHAT_ID environment variables")
        return
    
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event['data']).decode('utf-8')
        build_data = json.loads(pubsub_message)
        
        status = build_data.get('status')
        project_id = build_data.get('projectId')
        build_id = build_data.get('id')
        repo_name = build_data.get('substitutions', {}).get('REPO_NAME', 'Unknown')
        branch = build_data.get('substitutions', {}).get('BRANCH_NAME', 'Unknown')
        
        # Only send notifications for final statuses
        if status in ['SUCCESS', 'FAILURE', 'TIMEOUT', 'CANCELLED']:
            emoji = "✅" if status == "SUCCESS" else "❌"
            
            message = f"{emoji} *Build {status}*\n"
            message += f"📁 Project: `{project_id}`\n"
            message += f"🔗 Repo: `{repo_name}`\n"
            message += f"🌿 Branch: `{branch}`\n"
            message += f"🆔 Build ID: `{build_id}`"
            
            send_telegram_message(BOT_TOKEN, CHAT_ID, message)
            print(f"Successfully sent build notification for build {build_id}")
        else:
            print(f"Ignoring build status: {status}")
            
    except Exception as e:
        print(f"Error processing build notification: {e}")
        print(f"Cloud event data: {cloud_event}")

def invoice_notifier(cloud_event, context):
    """Cloud Function triggered by Pub/Sub topic for Invoice Creation notifications."""
    
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHAT_ID = os.environ.get('CHAT_ID')
    
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing BOT_TOKEN or CHAT_ID environment variables")
        return
    
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event['data']).decode('utf-8')
        invoice_data = json.loads(pubsub_message)
        
        event_type = invoice_data.get('event_type', 'invoice_creation')
        status = invoice_data.get('status')
        invoice_id = invoice_data.get('invoice_id')
        external_order_id = invoice_data.get('external_order_id')
        customer_name = invoice_data.get('customer_name', 'Unknown')
        amount = invoice_data.get('amount')
        currency = invoice_data.get('currency', 'EUR')
        error_message = invoice_data.get('error_message')
        
        # Determine emoji and message based on event type and status
        if event_type == 'invoice_creation':
            if status == 'success':
                emoji = "💰"
                message = f"{emoji} *Invoice Created Successfully*\n"
                message += f"🧾 Invoice ID: `{invoice_id}`\n"
                message += f"📋 Order ID: `{external_order_id}`\n"
                message += f"👤 Customer: `{customer_name}`\n"
                message += f"💵 Amount: `{amount} {currency}`"
            elif status == 'failure':
                emoji = "❌"
                message = f"{emoji} *Invoice Creation Failed*\n"
                message += f"📋 Order ID: `{external_order_id}`\n"
                message += f"👤 Customer: `{customer_name}`\n"
                if error_message:
                    message += f"🚨 Error: `{error_message}`"
            else:
                emoji = "⏳"
                message = f"{emoji} *Invoice Creation Attempt*\n"
                message += f"📋 Order ID: `{external_order_id}`\n"
                message += f"👤 Customer: `{customer_name}`\n"
                message += f"📊 Status: `{status}`"
        elif event_type == 'invoice_completion':
            if status == 'success':
                emoji = "✅"
                message = f"{emoji} *Invoice Completed & Fiscalized*\n"
                message += f"🧾 Invoice ID: `{invoice_id}`\n"
                message += f"📋 Order ID: `{external_order_id}`\n"
                message += f"👤 Customer: `{customer_name}`\n"
                message += f"💵 Amount: `{amount} {currency}`"
            else:
                emoji = "⚠️"
                message = f"{emoji} *Invoice Completion Issue*\n"
                message += f"🧾 Invoice ID: `{invoice_id}`\n"
                message += f"📋 Order ID: `{external_order_id}`\n"
                message += f"📊 Status: `{status}`"
                if error_message:
                    message += f"🚨 Error: `{error_message}`"
        else:
            # Generic invoice event
            emoji = "📄"
            message = f"{emoji} *Invoice Event: {event_type}*\n"
            message += f"🧾 Invoice ID: `{invoice_id}`\n"
            message += f"📋 Order ID: `{external_order_id}`\n"
            message += f"📊 Status: `{status}`"
        
        send_telegram_message(BOT_TOKEN, CHAT_ID, message)
        print(f"Successfully sent invoice notification for {event_type}: {invoice_id}")
        
    except Exception as e:
        print(f"Error processing invoice notification: {e}")
        print(f"Cloud event data: {cloud_event}")

def send_telegram_message(bot_token, chat_id, message):
    """Send a message to Telegram bot."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, json={
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    })
    
    if response.status_code != 200:
        print(f"Failed to send notification: {response.text}")
        raise Exception(f"Telegram API error: {response.status_code}")

def unified_notifier(cloud_event, context):
    """Unified Cloud Function that handles both build and invoice notifications."""
    
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHAT_ID = os.environ.get('CHAT_ID')
    
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing BOT_TOKEN or CHAT_ID environment variables")
        return
    
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event['data']).decode('utf-8')
        event_data = json.loads(pubsub_message)
        
        # Determine event type
        if 'projectId' in event_data and 'status' in event_data and 'id' in event_data:
            # This is a build event
            build_notifier(cloud_event, context)
        elif 'event_type' in event_data or 'invoice_id' in event_data:
            # This is an invoice event
            invoice_notifier(cloud_event, context)
        else:
            print(f"Unknown event type: {event_data}")
            
    except Exception as e:
        print(f"Error processing unified notification: {e}")
        print(f"Cloud event data: {cloud_event}")


# ===============================
# INVOICING SYSTEM MONITORING
# ===============================

def get_secret(secret_name: str, project_id: str = None) -> Optional[str]:
    """Get secret from Google Cloud Secret Manager."""
    if not project_id:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "lunette-minimax")
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Failed to get secret {secret_name}: {e}")
        return None


def get_database_connection():
    """Get database connection from Secret Manager."""
    database_url = get_secret("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL secret not found")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def send_telegram_alert(message: str) -> bool:
    """Send alert message to Telegram using the same credentials as other notifications."""
    # Reuse the existing BOT_TOKEN and CHAT_ID from environment or Secret Manager
    bot_token = os.environ.get('BOT_TOKEN') or get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get('CHAT_ID') or get_secret("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("Telegram alert sent successfully")
            return True
        else:
            print(f"Telegram API error: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False


def check_stuck_jobs(db_session) -> List[Dict[str, Any]]:
    """Check for orders that have been stuck for more than 24 hours."""
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    query = text("""
        SELECT 
            id,
            external_order_id,
            status,
            created_at,
            updated_at,
            retry_count,
            error_message,
            EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_stuck
        FROM orders 
        WHERE status IN ('PENDING', 'PROCESSING')
        AND created_at < :cutoff_time
        ORDER BY created_at ASC
    """)
    
    result = db_session.execute(query, {"cutoff_time": cutoff_time})
    stuck_jobs = []
    
    for row in result:
        stuck_jobs.append({
            "id": str(row.id),
            "external_order_id": row.external_order_id,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "retry_count": row.retry_count,
            "error_message": row.error_message,
            "hours_stuck": round(float(row.hours_stuck), 1)
        })
    
    return stuck_jobs


def check_worker_health() -> Dict[str, Any]:
    """Check if the invoicing service is healthy."""
    worker_urls = [
        os.getenv("WORKER_SERVICE_URL", "https://lunette-invoicing-898902894034.europe-west1.run.app/api/v1"),
        "https://lunette-invoicing-898902894034.europe-west1.run.app/api/v1",
    ]
    
    health_status = {
        "healthy": False,
        "url": None,
        "response_time": None,
        "error": None
    }
    
    for url in worker_urls:
        try:
            health_url = f"{url.rstrip('/')}/health"
            start_time = datetime.utcnow()
            
            response = requests.get(health_url, timeout=10)
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            if response.status_code == 200:
                health_status.update({
                    "healthy": True,
                    "url": health_url,
                    "response_time": round(response_time, 2),
                    "error": None
                })
                break
            else:
                health_status["error"] = f"HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            health_status["error"] = str(e)
            continue
    
    return health_status


def format_stuck_jobs_alert(stuck_jobs: List[Dict[str, Any]]) -> str:
    """Format stuck jobs for Telegram alert."""
    if not stuck_jobs:
        return ""
    
    message_parts = [
        "🚨 <b>STUCK JOBS ALERT</b>",
        f"Found {len(stuck_jobs)} jobs stuck for more than 24 hours:",
        ""
    ]
    
    for job in stuck_jobs[:5]:  # Limit to first 5 jobs
        message_parts.extend([
            f"📋 Order: <code>{job['external_order_id']}</code>",
            f"⏱ Stuck: {job['hours_stuck']} hours ({job['status']})",
            f"🔄 Retries: {job['retry_count']}",
        ])
        
        if job['error_message']:
            error_msg = job['error_message'][:100] + "..." if len(job['error_message']) > 100 else job['error_message']
            message_parts.append(f"❌ Error: <code>{error_msg}</code>")
        
        message_parts.append("")
    
    if len(stuck_jobs) > 5:
        message_parts.append(f"... and {len(stuck_jobs) - 5} more stuck jobs")
    
    return "\n".join(message_parts)


def format_worker_health_alert(health_status: Dict[str, Any]) -> str:
    """Format worker health alert for Telegram."""
    if health_status["healthy"]:
        return ""
    
    return f"""🔴 <b>WORKER HEALTH ALERT</b>

The invoicing worker service is not responding!

❌ Status: Unhealthy
🌐 Last checked: {health_status.get('url', 'Multiple URLs tried')}
⚠️ Error: {health_status.get('error', 'Unknown error')}

This means new invoice jobs may not be processed."""


@functions_framework.http
def monitor_invoicing_system(request):
    """
    Monitor invoicing system for stuck jobs and worker health.
    Designed to be triggered by Cloud Scheduler every hour.
    """
    try:
        print("Starting invoicing system monitoring...")
        
        # Get database connection
        db_session = get_database_connection()
        
        alerts = []
        
        # Check for stuck jobs
        print("Checking for stuck jobs...")
        stuck_jobs = check_stuck_jobs(db_session)
        if stuck_jobs:
            print(f"Found {len(stuck_jobs)} stuck jobs")
            stuck_jobs_alert = format_stuck_jobs_alert(stuck_jobs)
            if stuck_jobs_alert:
                alerts.append(stuck_jobs_alert)
        else:
            print("No stuck jobs found")
        
        # Check worker health
        print("Checking worker health...")
        health_status = check_worker_health()
        if not health_status["healthy"]:
            print("Worker health check failed")
            worker_alert = format_worker_health_alert(health_status)
            if worker_alert:
                alerts.append(worker_alert)
        else:
            print(f"Worker is healthy (response time: {health_status['response_time']}s)")
        
        # Send alerts if any issues found
        if alerts:
            for alert in alerts:
                success = send_telegram_alert(alert)
                if not success:
                    print("Failed to send Telegram alert")
        
        # Close database connection
        db_session.close()
        
        # Return monitoring results
        return {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "stuck_jobs_count": len(stuck_jobs),
            "worker_healthy": health_status["healthy"],
            "alerts_sent": len(alerts)
        }
        
    except Exception as e:
        print(f"Monitoring function failed: {e}")
        
        # Send error alert
        error_alert = f"""🚨 <b>MONITORING SYSTEM ERROR</b>

The invoicing monitoring system encountered an error:

❌ Error: <code>{str(e)[:200]}</code>
⏰ Time: {datetime.utcnow().isoformat()}

Please check the Cloud Function logs for more details."""
        
        send_telegram_alert(error_alert)
        
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 500