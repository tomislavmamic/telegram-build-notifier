# Telegram Build & Invoice Notifier + Monitoring

A comprehensive Google Cloud Function suite that handles:
1. **Build notifications** for Google Cloud Build status updates
2. **Invoice notifications** for real-time invoice events 
3. **System monitoring** for stuck jobs and worker health

## Features

### Build Notifications
- 📱 Real-time Telegram notifications for build completion
- ✅ Success/failure status with emoji indicators
- 📊 Detailed build information (project, repo, branch, build ID)
- 🔒 Secure environment variable configuration
- 🎯 Only notifies on final build statuses (SUCCESS, FAILURE, TIMEOUT, CANCELLED)

### Invoice Notifications  
- 💰 Real-time notifications for invoice creation attempts
- 📄 Support for different invoice events (creation, completion, failure)
- 👤 Customer and order information included
- 💵 Amount and currency details
- 🚨 Error reporting for failed invoice attempts

### System Monitoring (NEW!)
- 🔍 **Stuck Job Detection**: Finds orders stuck in PENDING/PROCESSING for >24 hours
- 🏥 **Worker Health Checks**: Monitors if the invoicing worker service is responding
- 🎯 **On-Demand Monitoring**: Run manually when you suspect issues
- 🚨 **Smart Alerts**: Only sends notifications when problems are found
- 📊 **Processing Stats**: Tracks overall system health metrics

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command and follow the prompts
3. Save your bot token

### 2. Get Your Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
3. Find your chat ID in the response

### 3. Deploy the Functions

1. Copy `.env.yaml.template` to `.env.yaml` and fill in your credentials:
   ```yaml
   BOT_TOKEN: "your_bot_token_here"
   CHAT_ID: "your_chat_id_here"
   ```

2. Enable required APIs:
   ```bash
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable eventarc.googleapis.com
   ```

3. Create Pub/Sub topics:
   ```bash
   gcloud pubsub topics create cloud-builds
   gcloud pubsub topics create invoice-notifications
   ```

4. Deploy the build notification function:
   ```bash
   gcloud functions deploy build_notifier \
     --runtime python311 \
     --trigger-topic cloud-builds \
     --env-vars-file .env.yaml \
     --region us-central1 \
     --no-gen2
   ```

5. Deploy the invoice notification function:
   ```bash
   gcloud functions deploy invoice_notifier \
     --runtime python311 \
     --trigger-topic invoice-notifications \
     --env-vars-file .env.yaml \
     --region us-central1 \
     --no-gen2
   ```

6. **Alternative: Deploy unified function (handles both build and invoice events)**:
   ```bash
   gcloud functions deploy unified_notifier \
     --runtime python311 \
     --trigger-topic cloud-builds \
     --env-vars-file .env.yaml \
     --region us-central1 \
     --no-gen2
   ```

7. **Deploy monitoring function (checks for stuck jobs and worker health)**:
   ```bash
   gcloud functions deploy monitor_invoicing_system \
     --runtime python311 \
     --trigger-http \
     --allow-unauthenticated \
     --env-vars-file .env.yaml \
     --region us-central1 \
     --timeout 540 \
     --memory 256MB
   ```

8. **Optional: Set up monitoring schedule (only if you want automated checks)**:
   ```bash
   # Get the monitoring function URL first
   MONITOR_URL=$(gcloud functions describe monitor_invoicing_system --region=us-central1 --format="value(httpsTrigger.url)")
   
   # Create daily monitoring schedule (optional)
   gcloud scheduler jobs create http invoicing-monitor-job \
     --schedule="0 9 * * *" \
     --uri="$MONITOR_URL" \
     --http-method=GET \
     --location=us-central1 \
     --description="Daily morning check of invoicing system health"
   
   # OR just keep it for manual triggering - no scheduler needed!
   ```

### 4. Test the Setup

#### Test Build Notifications
Trigger a test build:
```bash
echo 'FROM alpine:latest
RUN echo "Test build"' > Dockerfile

gcloud builds submit --tag gcr.io/YOUR_PROJECT/test-build .
```

#### Test Invoice Notifications
Test invoice notifications by creating a test invoice through your invoicing API:
```bash
curl -X POST https://your-invoicing-api.com/api/v1/invoices \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "external_order_id": "test-order-123",
    "customerDetails": {
      "name": "Test Customer",
      "email": "test@example.com"
    },
    "items": [
      {
        "name": "Test Item",
        "quantity": 1,
        "price": 10.00
      }
    ]
  }'
```

You should receive Telegram notifications for both build and invoice events!

#### Test Monitoring System
Test the monitoring system:
```bash
# Test locally (requires database access)
python test_monitoring.py

# Send a real test message to Telegram  
python test_monitoring.py --send-telegram-test

# Test the deployed function directly
curl "https://europe-west1-lunette-minimax.cloudfunctions.net/monitor_invoicing_system"

# Manually trigger monitoring when you suspect issues
curl "https://europe-west1-lunette-minimax.cloudfunctions.net/monitor_invoicing_system"
```

## Message Formats

### Build Notifications
- ✅/❌ Build status with emoji
- 📁 GCP Project name
- 🔗 Repository name (when available)
- 🌿 Branch name (when available)
- 🆔 Build ID for reference

### Invoice Notifications
- 💰 Invoice creation success
- ❌ Invoice creation failure
- ✅ Invoice completion & fiscalization
- 🧾 Invoice ID
- 📋 External order ID
- 👤 Customer name
- 💵 Amount and currency
- 🚨 Error messages (for failures)

### Monitoring Alerts
**Stuck Jobs Alert:**
```
🚨 STUCK JOBS ALERT
Found 3 jobs stuck for more than 24 hours:

📋 Order: 6572612223250
⏱ Stuck: 26.4 hours (PENDING)
🔄 Retries: 0

📋 Order: 6572612223251
⏱ Stuck: 25.1 hours (PROCESSING)
🔄 Retries: 2
❌ Error: Failed to create invoice in Minimax
```

**Worker Health Alert:**
```
🔴 WORKER HEALTH ALERT

The invoicing worker service is not responding!

❌ Status: Unhealthy
🌐 Last checked: https://worker-url/health
⚠️ Error: Connection timeout

This means new invoice jobs may not be processed.
```

## Security

- Bot token and chat ID are stored as environment variables or Secret Manager
- Functions only process authorized events (Cloud Build, invoice notifications, monitoring)
- Database credentials stored securely in Secret Manager
- No sensitive information is logged
- HTTP monitoring endpoint is unauthenticated but safe (read-only operations)

## Troubleshooting

Check function logs:
```bash
# Build notifications
gcloud functions logs read build_notifier --region us-central1 --limit 10

# Invoice notifications  
gcloud functions logs read invoice_notifier --region us-central1 --limit 10

# Monitoring system
gcloud functions logs read monitor_invoicing_system --region us-central1 --limit 10

# Unified notifier
gcloud functions logs read unified_notifier --region us-central1 --limit 10
```

### Common Issues

**Monitoring alerts not working:**
- Verify `DATABASE_URL` secret exists in Secret Manager
- Check if monitoring function has database access
- Test with `python test_monitoring.py --send-telegram-test`

**Database connection issues:**
- Ensure Cloud SQL Auth Proxy is not required
- Verify database connection string format
- Check network/firewall settings

**No notifications received:**
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured
- Test with a simple curl to the function endpoint  
- Check Cloud Function logs for errors

## Requirements

- Google Cloud Project with Cloud Build enabled
- Telegram account and bot
- gcloud CLI configured