# Setting Up Gmail API Credentials

## Quick Setup

1. Copy the example credentials file:
   ```bash
   cp credentials.json.example credentials.json
   ```

2. Edit `credentials.json` and replace:
   - `YOUR_CLIENT_ID` with your actual Client ID from Google Cloud Console
   - `YOUR_CLIENT_SECRET` with your actual Client Secret from Google Cloud Console

## Getting Client ID and Client Secret

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Click "Create"
   - You'll see your **Client ID** and **Client Secret**
   - Copy these values into the `credentials.json` file

## Minimal Credentials Structure

If you only have Client ID and Client Secret, use this structure in `credentials.json`:

```json
{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "client_secret": "your-client-secret",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Note

The `credentials.json` file is gitignored for security reasons. Never commit your actual credentials to version control.
