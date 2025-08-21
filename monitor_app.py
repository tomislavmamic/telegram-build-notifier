#!/usr/bin/env python3
"""
Monitoring service for monitor.lunette.hr
Standalone service to monitor the invoicing system.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests
from flask import Flask, request, jsonify, render_template_string

# Import monitoring functions from main.py
from main import (
    get_secret, send_telegram_alert, check_stuck_jobs, check_worker_health,
    format_stuck_jobs_alert, format_worker_health_alert,
    get_database_connection
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Simple HTML template for the monitoring dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Invoicing System Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               margin: 40px; background: #f8f9fa; }
        .container { max-width: 800px; margin: 0 auto; background: white; 
                    padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; margin-bottom: 30px; }
        .status { padding: 15px; margin: 15px 0; border-radius: 5px; font-weight: bold; }
        .status.healthy { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
        .status.warning { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
        .status.error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
        .button { background: #007bff; color: white; padding: 12px 24px; 
                 border: none; border-radius: 5px; cursor: pointer; text-decoration: none; 
                 display: inline-block; margin: 10px 5px 0 0; }
        .button:hover { background: #0056b3; color: white; text-decoration: none; }
        .button.danger { background: #dc3545; }
        .button.danger:hover { background: #c82333; }
        .details { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .timestamp { color: #6c757d; font-size: 0.9em; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .loading { text-align: center; padding: 40px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Invoicing System Monitor</h1>
        <div class="timestamp">Last updated: <span id="timestamp">{{ timestamp }}</span></div>
        
        <div id="status-container">
            {% if status == 'loading' %}
                <div class="loading">Loading system status...</div>
            {% elif status == 'healthy' %}
                <div class="status healthy">
                    ✅ System Status: All systems operational
                </div>
            {% elif stuck_jobs_count > 0 or not worker_healthy %}
                <div class="status error">
                    🚨 Issues Detected
                </div>
            {% endif %}
        </div>

        {% if stuck_jobs_count > 0 %}
        <div class="details">
            <h3>🚨 Stuck Jobs ({{ stuck_jobs_count }})</h3>
            <p>Orders stuck in PENDING/PROCESSING status for more than 24 hours:</p>
            <ul>
            {% for job in stuck_jobs %}
                <li><strong>Order {{ job.external_order_id }}</strong>: {{ job.hours_stuck }}h in {{ job.status }} status
                    {% if job.error_message %}<br><small>Error: {{ job.error_message[:100] }}...</small>{% endif %}
                </li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div class="details">
            <h3>🏥 Worker Health</h3>
            {% if worker_healthy %}
                <div class="status healthy">Worker service is healthy ({{ worker_response_time }}s response time)</div>
            {% else %}
                <div class="status error">Worker service is not responding: {{ worker_error }}</div>
            {% endif %}
        </div>

        <div style="margin-top: 40px;">
            <a href="/monitor" class="button">🔄 Run Check Now</a>
            <a href="/monitor?format=json" class="button">📊 JSON API</a>
            {% if stuck_jobs_count > 0 %}
                <a href="/send-alert" class="button danger">📱 Send Telegram Alert</a>
            {% endif %}
        </div>

        <div class="details">
            <h3>ℹ️ About</h3>
            <p>This monitoring system checks:</p>
            <ul>
                <li><strong>Stuck Jobs:</strong> Orders that have been in PENDING/PROCESSING status for more than 24 hours</li>
                <li><strong>Worker Health:</strong> Whether the invoicing worker service is responding to health checks</li>
            </ul>
            <p>Alerts are automatically sent to Telegram when issues are detected.</p>
        </div>
    </div>

    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 5 * 60 * 1000);
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
@app.route('/monitor', methods=['GET'])
def monitor_dashboard():
    """Main monitoring endpoint with dashboard or JSON response."""
    format_type = request.args.get('format', 'html')
    
    try:
        logger.info("Starting invoicing system monitoring...")
        
        # Get database connection
        db_session = get_database_connection()
        
        alerts = []
        
        # Check for stuck jobs
        stuck_jobs = check_stuck_jobs(db_session)
        if stuck_jobs:
            logger.warning(f"Found {len(stuck_jobs)} stuck jobs")
            stuck_jobs_alert = format_stuck_jobs_alert(stuck_jobs)
            if stuck_jobs_alert:
                alerts.append(stuck_jobs_alert)
        
        # Check worker health
        health_status = check_worker_health()
        if not health_status["healthy"]:
            logger.warning("Worker health check failed")
            worker_alert = format_worker_health_alert(health_status)
            if worker_alert:
                alerts.append(worker_alert)
        
        # Send alerts if any issues found
        alert_sent = False
        if alerts:
            for alert in alerts:
                success = send_telegram_alert(alert)
                if success:
                    alert_sent = True
        
        db_session.close()
        
        # Determine overall status
        overall_status = "healthy"
        if stuck_jobs or not health_status["healthy"]:
            overall_status = "issues"
        
        result = {
            "status": "completed",
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "stuck_jobs_count": len(stuck_jobs),
            "stuck_jobs": stuck_jobs,
            "worker_healthy": health_status["healthy"],
            "worker_status": health_status,
            "alerts_sent": len(alerts),
            "telegram_alert_sent": alert_sent
        }
        
        if format_type == 'json':
            return jsonify(result)
        
        # Render HTML dashboard
        return render_template_string(DASHBOARD_TEMPLATE,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            status=overall_status,
            stuck_jobs_count=len(stuck_jobs),
            stuck_jobs=stuck_jobs,
            worker_healthy=health_status["healthy"],
            worker_response_time=health_status.get("response_time", "N/A"),
            worker_error=health_status.get("error", "Unknown error")
        )
        
    except Exception as e:
        logger.error(f"Monitoring function failed: {e}")
        
        # Send error alert
        error_alert = f"""🚨 <b>MONITORING SYSTEM ERROR</b>

The invoicing monitoring system encountered an error:

❌ Error: <code>{str(e)[:200]}</code>
⏰ Time: {datetime.utcnow().isoformat()}

Please check the service logs for more details."""
        
        send_telegram_alert(error_alert)
        
        if format_type == 'json':
            return jsonify({
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
        
        return render_template_string(DASHBOARD_TEMPLATE,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            status="error",
            stuck_jobs_count=0,
            stuck_jobs=[],
            worker_healthy=False,
            worker_response_time="N/A",
            worker_error=str(e)
        ), 500


@app.route('/send-alert', methods=['POST', 'GET'])
def send_test_alert():
    """Send a test alert to Telegram."""
    try:
        test_message = f"""🧪 <b>TEST ALERT</b>

This is a manual test alert from the monitoring system.

⏰ Time: {datetime.utcnow().isoformat()}
🌐 Source: monitor.lunette.hr

If you receive this message, Telegram notifications are working correctly!"""
        
        success = send_telegram_alert(test_message)
        
        if request.args.get('format') == 'json':
            return jsonify({
                "status": "success" if success else "failed",
                "message": "Test alert sent" if success else "Failed to send test alert",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Redirect back to dashboard
        return f"""
        <script>
            alert('{"Test alert sent successfully!" if success else "Failed to send test alert"}');
            window.location.href = '/';
        </script>
        """
        
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        if request.args.get('format') == 'json':
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
        
        return f"""
        <script>
            alert('Error sending test alert: {str(e)}');
            window.location.href = '/';
        </script>
        """


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "invoicing-monitoring",
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)