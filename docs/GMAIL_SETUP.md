# Gmail Integration Setup Guide

## Prerequisites
- Google account
- CloneAI installed and configured

## Step 1: Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

## Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in app name: "CloneAI"
   - Add your email as a test user
   - Add scopes: `https://www.googleapis.com/auth/gmail.readonly`
4. For "Application type", select "Desktop app"
5. Name it "CloneAI Desktop"
6. Click "Create"

## Step 3: Download Credentials

1. After creating, click the download icon (⬇️) next to your OAuth 2.0 Client ID
2. Save the file as `credentials.json`
3. Move it to: `C:\Users\<YourUsername>\.clai\credentials.json`

### Quick Setup (PowerShell):
```powershell
# Create .clai directory
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.clai"

# Move your downloaded credentials file
Move-Item "C:\Users\<YourUsername>\Downloads\credentials.json" "$env:USERPROFILE\.clai\credentials.json"
```

## Step 4: First-Time Authentication

Run any mail command for the first time:
```powershell
clai do "mail:list last 5"
```

This will:
1. Open your browser
2. Ask you to sign in to Google
3. Request permission to read your Gmail
4. Save the authentication token to `~/.clai/token.pickle`

## Usage Examples

### List last 5 emails (default)
```powershell
clai do "mail:list"
clai do "mail:list last 5"
```

### List last 10 emails
```powershell
clai do "mail:list last 10"
```

### List emails from specific sender
```powershell
clai do "mail:list john@example.com"
clai do "mail:list support@github.com"
```

### Combine filters
```powershell
clai do "mail:list john@example.com last 3"
clai do "mail:list last 3 john@example.com"
```

## Troubleshooting

### Error: "Credentials file not found"
- Make sure `credentials.json` is in `C:\Users\<YourUsername>\.clai\`
- Check the path: `Test-Path "$env:USERPROFILE\.clai\credentials.json"`

### Error: "Access blocked: Authorization Error"
- Go back to OAuth consent screen
- Add your email to "Test users"
- Make sure the app is in "Testing" mode

### Error: "The file token.pickle cannot be opened"
- Delete the token: `Remove-Item "$env:USERPROFILE\.clai\token.pickle"`
- Run the command again to re-authenticate

### Error: "Gmail API has not been used in project"
- Make sure Gmail API is enabled in your Google Cloud project
- Wait a few minutes after enabling (can take up to 5 minutes)

## Security Notes

- `credentials.json` contains your OAuth client ID and secret
- `token.pickle` contains your authenticated session
- Keep both files secure and don't share them
- Both files are stored in `~/.clai/` (user home directory)
- Add `.clai/` to your `.gitignore` if sharing code

## File Locations

```
C:\Users\<YourUsername>\.clai\
├── credentials.json    (OAuth credentials from Google Cloud)
└── token.pickle       (Auto-generated after first auth)
```
