# Telegram Build Notifier

A Google Cloud Function that sends Telegram notifications for Google Cloud Build status updates.

## Features

- 📱 Real-time Telegram notifications for build completion
- ✅ Success/failure status with emoji indicators
- 📊 Detailed build information (project, repo, branch, build ID)
- 🔒 Secure environment variable configuration
- 🎯 Only notifies on final build statuses (SUCCESS, FAILURE, TIMEOUT, CANCELLED)

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command and follow the prompts
3. Save your bot token

### 2. Get Your Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates`
3. Find your chat ID in the response

### 3. Deploy the Function

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

3. Create Pub/Sub topic:
   ```bash
   gcloud pubsub topics create cloud-builds
   ```

4. Deploy the function:
   ```bash
   gcloud functions deploy build_notifier \
     --runtime python311 \
     --trigger-topic cloud-builds \
     --env-vars-file .env.yaml \
     --region us-central1 \
     --no-gen2
   ```

### 4. Test the Setup

Trigger a test build:
```bash
echo 'FROM alpine:latest
RUN echo "Test build"' > Dockerfile

gcloud builds submit --tag gcr.io/YOUR_PROJECT/test-build .
```

You should receive a Telegram notification when the build completes!

## Message Format

The notifications include:
- ✅/❌ Build status with emoji
- 📁 GCP Project name
- 🔗 Repository name (when available)
- 🌿 Branch name (when available)
- 🆔 Build ID for reference

## Security

- Bot token and chat ID are stored as environment variables
- Function only processes Cloud Build events
- No sensitive information is logged

## Troubleshooting

Check function logs:
```bash
gcloud functions logs read build_notifier --region us-central1 --limit 10
```

## Requirements

- Google Cloud Project with Cloud Build enabled
- Telegram account and bot
- gcloud CLI configured