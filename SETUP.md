# Reddit API Setup Guide

To fix 401 errors and enable full functionality, you need to set up Reddit API credentials.

## Quick Setup

1. **Create a Reddit App:**
   - Go to https://www.reddit.com/prefs/apps
   - Click "create another app..." or scroll down and click "create app"
   - Fill in:
     - **Name**: Reddit Image Viewer (or any name)
     - **Type**: Select **"script"**
     - **Description**: (optional)
     - **Redirect URI**: Leave blank or use `http://localhost:8001`
   - Click "create app"

2. **Get Your Credentials:**
   - After creating, you'll see your app listed
   - **Client ID**: The string under your app name (looks like random characters)
   - **Secret**: The "secret" field (click "edit" if you need to see it)

3. **Configure the App:**
   
   **Option A: Using .env file (Recommended)**
   ```bash
   cp env.example .env
   # Then edit .env and add your credentials:
   # REDDIT_CLIENT_ID=your_actual_client_id
   # REDDIT_CLIENT_SECRET=your_actual_secret
   ```

   **Option B: Using Environment Variables**
   ```bash
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"
   ```

4. **Restart the Server:**
   ```bash
   # Stop the current server, then:
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Verification

When you start the server, you should see:
- `✓ Reddit API: Authenticated mode` - if credentials are set correctly
- `⚠ Reddit API: Unauthenticated mode` - if credentials are missing

## Troubleshooting

- **401 Unauthorized**: Make sure your credentials are correct and the app type is "script"
- **Rate Limit Errors**: Authenticated mode has much higher rate limits
- **Still getting 401**: Double-check that your .env file is in the project root and has the correct format

