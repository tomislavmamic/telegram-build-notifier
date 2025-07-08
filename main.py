import json
import requests
import base64
import os
from google.cloud import functions_v1

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
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            })
            
            if response.status_code == 200:
                print(f"Successfully sent notification for build {build_id}")
            else:
                print(f"Failed to send notification: {response.text}")
        else:
            print(f"Ignoring build status: {status}")
            
    except Exception as e:
        print(f"Error processing build notification: {e}")
        print(f"Cloud event data: {cloud_event}")