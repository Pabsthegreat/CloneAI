# CloneAI - Complete Setup & Usage Guide

**Your all-in-one guide to install, configure, and use CloneAI.**

---

## 📖 Table of Contents

1. [What is CloneAI?](#what-is-cloneai)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [PowerShell Auto-Load Setup](#powershell-auto-load-setup)
5. [Gmail API Setup (Email Features)](#gmail-api-setup-email-features)
6. [Available Commands](#available-commands)
7. [Troubleshooting](#troubleshooting)
8. [Command Reference](#command-reference)
9. [Tips & Best Practices](#tips--best-practices)

---

## What is CloneAI?

CloneAI is a personal AI assistant that runs in your Windows PowerShell command line. You can use it to:

- 📧 **Check and manage emails** from Gmail
- 💬 **Chat with an AI assistant** for help and automation
- 📝 **Track command history** (automatically stores last 100 commands)
- 🔧 **Extend with custom tools** - add your own integrations
- 🔒 **Run privately** - everything runs locally on your machine

---

## Prerequisites

Before you start, make sure you have:

- ✅ **Windows 10/11** with PowerShell
- ✅ **Python 3.10 or higher** - [Download here](https://www.python.org/downloads/)
  - ⚠️ **Important**: Check "Add Python to PATH" during installation
- ✅ **Internet connection** (for Gmail API setup)
- ✅ **Google account** (optional, for email features)

### Check if Python is Installed

1. Press `Windows Key + X`
2. Click "PowerShell" or "Windows Terminal"
3. Type: `python --version`

**If you see a version number** (like `Python 3.10.1`): ✅ Great! Continue to installation.

**If you see an error**: ❌ Install Python:
1. Go to https://www.python.org/downloads/
2. Click "Download Python"
3. Run installer
4. **CHECK** the box "Add Python to PATH"
5. Click "Install Now"
6. Close and reopen PowerShell

---

## Installation

CloneAI automatically detects your operating system and adapts accordingly. When you run commands, you'll see your system info displayed: `System: Windows (x86_64)`, `System: macOS Silicon`, or `System: Linux (x86_64)`.

### Step 1: Get the Code

**Option A: Download ZIP** (Easiest)
1. Download CloneAI repository as ZIP
2. Extract to:
   - **Windows:** `C:\Users\<YourUsername>\OneDrive\Documents\CloneAI`
   - **macOS/Linux:** `~/Documents/CloneAI`

**Option B: Clone with Git**
```bash
# Windows (PowerShell)
cd C:\Users\<YourUsername>\OneDrive\Documents
git clone https://github.com/Pabsthegreat/CloneAI.git
cd CloneAI

# macOS/Linux (Bash/Zsh)
cd ~/Documents
git clone https://github.com/Pabsthegreat/CloneAI.git
cd CloneAI
```

### Step 2: Install Dependencies

**Windows (PowerShell):**
```powershell
# Navigate to CloneAI directory
cd C:\Users\<YourUsername>\OneDrive\Documents\CloneAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

**If you get "running scripts is disabled" error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try activating again: `.\.venv\Scripts\Activate.ps1`

**Continue installation (Windows):**
```powershell
# Install required packages (takes 1-2 minutes)
pip install -r requirements.txt

# Install email package
pip install google-auth-oauthlib
```

**macOS/Linux (Bash/Zsh):**
```bash
# Navigate to CloneAI directory
cd ~/Documents/CloneAI

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install required packages (takes 1-2 minutes)
pip install -r requirements.txt

# Install email package
pip install google-auth-oauthlib
```

### Step 3: Test Basic Installation

**Windows:**
```powershell
# Test if CloneAI works
python -m agent.cli --help
```

**macOS/Linux:**
```bash
# Test if CloneAI works
python3 -m agent.cli --help
```

You should see `System: <YourSystem>` followed by a list of available commands. If you do, **installation successful!** ✅

---

## Shell Auto-Load Setup

Make CloneAI available **automatically** every time you open your terminal.

### Windows (PowerShell)

**Step 1: Add to PowerShell Profile**

Run this command (replace `<YourUsername>` with your actual username):

```powershell
Add-Content $PROFILE "`n# CloneAI Auto-Load`n. 'C:\Users\<YourUsername>\OneDrive\Documents\CloneAI\setup-clai.ps1'"
```

**Step 2: Reload Profile**

```powershell
. $PROFILE
```

You should see:
```
System: Windows (x86_64)
✅ CloneAI commands loaded!
   Use: clai hi
   Use: clai chat 'your message'
   Use: clai-cd (to navigate to CloneAI directory)
```

**Step 3: Verify Auto-Load**

1. **Close PowerShell completely**
2. **Open a new PowerShell window**
3. Type: `clai --help`

### macOS/Linux (Bash/Zsh)

**Step 1: Make setup script executable**

```bash
chmod +x ~/Documents/CloneAI/setup-clai.sh
```

**Step 2: Add to shell profile**

For **Bash** (most Linux, older macOS):
```bash
echo "source ~/Documents/CloneAI/setup-clai.sh" >> ~/.bashrc
source ~/.bashrc
```

For **Zsh** (modern macOS default):
```bash
echo "source ~/Documents/CloneAI/setup-clai.sh" >> ~/.zshrc
source ~/.zshrc
```

You should see:
```
System: macOS Silicon  (or Linux (x86_64))
✅ CloneAI commands loaded!
   Use: clai hi
   Use: clai chat 'your message'
   Use: clai-cd (to navigate to CloneAI directory)
```

**Step 3: Verify Auto-Load**

1. **Close terminal completely**
2. **Open a new terminal window**
3. Type: `clai --help`

If you see the help menu, **auto-load is working!** ✅ You'll never need to manually load CloneAI again.

### Managing Your Profile

**View your profile:**
```powershell
notepad $PROFILE
# or
code $PROFILE  # if you have VS Code
```

**Profile location:**
```
C:\Users\<YourUsername>\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

**Remove auto-load** (if needed):
Edit `$PROFILE` and delete the CloneAI lines.

---

## Gmail API Setup (Email & Calendar Features)

To use email commands (like `clai do "mail:list last 5"`) and calendar commands (like `clai do "calendar:create..."`), you need Google API credentials.

> **Note**: The same credentials work for both Gmail and Google Calendar! You only need to set this up once.

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click **"Select a project"** at the top
4. Click **"NEW PROJECT"**
5. Name: `CloneAI`
6. Click **"CREATE"**
7. Wait for project creation (takes ~30 seconds)

### Step 2: Enable Gmail API and Google Calendar API

1. Make sure your CloneAI project is selected
2. Go to **"APIs & Services"** > **"Library"** (left menu)
3. Search for: `Gmail API`
4. Click on **"Gmail API"**
5. Click **"ENABLE"**
6. Wait for it to enable
7. Click **"Library"** again in the left menu
8. Search for: `Google Calendar API`
9. Click on **"Google Calendar API"**
10. Click **"ENABLE"**
11. Wait for it to enable

### Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Choose **"External"** user type
3. Click **"CREATE"**
4. Fill in the form:
   - **App name**: `CloneAI`
   - **User support email**: (your email)
   - **Developer contact email**: (your email)
5. Click **"SAVE AND CONTINUE"**
6. Click **"ADD OR REMOVE SCOPES"**
7. Add the following scopes (search and check each one):
   - `gmail.readonly` - Read emails
   - `gmail.compose` - Create drafts
   - `gmail.send` - Send emails
   - `calendar` - Manage calendar events
8. Click **"UPDATE"**
9. Click **"SAVE AND CONTINUE"**
10. Under **"Test users"**, click **"ADD USERS"**
11. Enter your Gmail address
12. Click **"ADD"**
13. Click **"SAVE AND CONTINUE"**
14. Click **"BACK TO DASHBOARD"**

### Step 4: Create OAuth Credentials

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"CREATE CREDENTIALS"** at the top
3. Choose **"OAuth client ID"**
4. Application type: **"Desktop app"**
5. Name: `CloneAI Desktop`
6. Click **"CREATE"**
7. Click **"OK"** on the confirmation popup

### Step 5: Download Credentials

1. You'll see your new credential in the list
2. Click the **download icon** (⬇️) on the right side
3. The file will download (named like `client_secret_xxxxx.json`)
4. **Rename** the file to: `credentials.json`

### Step 6: Install Credentials

Run these commands in PowerShell:

```powershell
# Create .clai directory in your user folder
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.clai"

# Move credentials from Downloads to .clai folder
Move-Item "$env:USERPROFILE\Downloads\credentials.json" "$env:USERPROFILE\.clai\credentials.json"
```

**If credentials.json is elsewhere** (like in the CloneAI project folder):
```powershell
Copy-Item "C:\Users\<YourUsername>\OneDrive\Documents\CloneAI\credentials.json" "$env:USERPROFILE\.clai\credentials.json" -Force
```

**Verify credentials are in place:**
```powershell
Test-Path "$env:USERPROFILE\.clai\credentials.json"
```
Should return: `True`

### Step 7: First-Time Authentication

Run your first email command:

```powershell
clai do "mail:list last 5"
```

**What happens next:**
1. Your browser will open automatically
2. Sign in to your Google account
3. You'll see "CloneAI wants access to your Google Account"
4. Click **"Continue"** (it may show a warning - that's OK, you're a test user)
5. Click **"Allow"** to grant Gmail and Calendar access
6. You can close the browser
7. Go back to PowerShell - your emails should be listed!

**Authentication complete!** ✅ Your credentials are saved and will be reused automatically:
- `~/.clai/token.pickle` - For Gmail (list emails, create drafts)
- `~/.clai/token_calendar.pickle` - For Google Calendar (create/list events)

> **Note**: When you first use a calendar command, you'll be prompted to authenticate again for Calendar API access. This is normal - just follow the same browser steps.

### Common Gmail Setup Issues

**"Created Web App credentials instead of Desktop App"**

If you accidentally selected "Web application" instead of "Desktop app":

```powershell
# Delete the wrong credential in Google Cloud Console
# Create a new one (Desktop app), download as credentials.json
# Then replace the old file:
Copy-Item "$env:USERPROFILE\Downloads\credentials.json" "$env:USERPROFILE\.clai\credentials.json" -Force

# Delete old authentication token
Remove-Item "$env:USERPROFILE\.clai\token.pickle" -ErrorAction SilentlyContinue

# Re-authenticate
clai do "mail:list last 5"
```

**"Access blocked: Authorization Error"**
- Make sure you added yourself as a **Test user** in OAuth consent screen
- Make sure app is in **"Testing"** mode (not published)

**"Gmail API has not been used in project"**
- Make sure Gmail API is **enabled** in your project
- Wait 2-5 minutes after enabling, then try again

---

## Available Commands

Once installed, you can use these commands anywhere in PowerShell:

### Basic Commands

```powershell
# Interactive greeting - prompts for your input
clai hi

# Chat directly with the AI
clai chat "help me organize my tasks"

# Get help and see all commands
clai --help

# Get help for specific command
clai do --help
```

### Email Commands

#### List Emails

All email list commands use the format: `clai do "mail:list [options]"`

```powershell
# List last 5 emails (default)
clai do "mail:list"
clai do "mail:list last 5"

# List specific number of emails
clai do "mail:list last 10"
clai do "mail:list last 20"

# List emails from specific sender
clai do "mail:list boss@company.com"
clai do "mail:list support@github.com"
clai do "mail:list john@example.com"

# Combine filters (order doesn't matter)
clai do "mail:list boss@company.com last 3"
clai do "mail:list last 3 boss@company.com"
```

**Email output example:**
```
📧 Found 3 email(s):
================================================================================

1. From: John Doe <john@example.com>
   Subject: Meeting Tomorrow
   Date: Fri, 11 Oct 2024 14:30:00 +0000
   Preview: Hi team, just a reminder about tomorrow's meeting...
--------------------------------------------------------------------------------

2. From: GitHub <noreply@github.com>
   Subject: [Repo] Pull request merged
   Date: Fri, 11 Oct 2024 10:15:00 +0000
   Preview: Your pull request #123 has been successfully merged...
--------------------------------------------------------------------------------

3. From: Support <support@company.com>
   Subject: Your ticket has been resolved
   Date: Thu, 10 Oct 2024 16:45:00 +0000
   Preview: Good news! Your support ticket #456 has been resolved...
================================================================================
```

#### Create Email Drafts

Create email drafts that appear in your Gmail drafts folder:

```powershell
# Basic draft
clai do "mail:draft to:recipient@example.com subject:Hello body:This is my message"

# Draft with CC
clai do "mail:draft to:team@company.com subject:Weekly Update body:Here is the update cc:manager@company.com"

# Draft with BCC
clai do "mail:draft to:client@external.com subject:Proposal body:Please review bcc:sales@company.com"

# Draft with both CC and BCC
clai do "mail:draft to:user@test.com subject:Meeting body:Let's meet tomorrow cc:alice@test.com bcc:bob@test.com"
```

**Draft output example:**
```
✅ Draft created successfully!

Draft ID: r-1234567890
To: recipient@example.com
Subject: Hello

You can find this draft in your Gmail drafts folder.
```

#### View Email Drafts

List all your Gmail drafts:

```powershell
# List all drafts (default: 10)
clai do "mail:drafts"

# List last 5 drafts
clai do "mail:drafts last 5"

# List last 20 drafts
clai do "mail:drafts last 20"
```

**Drafts output example:**
```
📝 Found 3 draft(s):
================================================================================

1. Draft ID: r1234567890
   To: user@example.com
   Subject: Meeting Follow-up
   Preview: Thank you for taking the time to meet...
--------------------------------------------------------------------------------

2. Draft ID: r0987654321
   To: team@company.com
   Subject: Project Update
   Preview: Here's the status update for this week...
--------------------------------------------------------------------------------
```

#### Send Emails

Send emails directly (not as drafts):

```powershell
# Basic email
clai do "mail:send to:recipient@example.com subject:Hello body:This is my message"

# Email with CC
clai do "mail:send to:team@company.com subject:Update body:Status report cc:manager@company.com"

# Email with BCC
clai do "mail:send to:client@external.com subject:Invoice body:Payment due bcc:accounting@company.com"
```

#### Send Emails with Attachments

Attach files to your emails:

```powershell
# Single attachment
clai do "mail:send to:user@test.com subject:Document body:Please review attachments:C:\Users\Me\report.pdf"

# Multiple attachments (comma-separated, no spaces)
clai do "mail:send to:client@test.com subject:Files body:See attached attachments:C:\file1.pdf,C:\file2.docx,C:\image.jpg"

# With CC and attachments
clai do "mail:send to:team@work.com subject:Report body:Q4 numbers cc:boss@work.com attachments:C:\Q4-report.xlsx"
```

**Important notes about attachments:**
- Use absolute paths (e.g., `C:\Users\Me\file.pdf`)
- Gmail limit: 25 MB total per email
- All file types supported
- Separate multiple files with commas (no spaces)

#### Send Existing Draft

Send a draft by its ID (get IDs from `mail:drafts`):

```powershell
# First, list drafts to get the ID
clai do "mail:drafts"

# Then send by ID
clai do "mail:send draft-id:r1234567890"
```

**Send output example:**
```
✅ Email sent successfully!

Message ID: 18c5a2b3d4e5f6g7
To: recipient@example.com
Subject: Hello
```

### Calendar Commands

#### Create Calendar Events

Create events in your Google Calendar:

```powershell
# Basic event with title and start time (1 hour duration by default)
clai do "calendar:create title:Team Meeting start:2025-10-15T14:00:00 duration:60"

# Event with end time instead of duration
clai do "calendar:create title:Lunch start:2025-10-15T12:00:00 end:2025-10-15T13:00:00"

# Event with location
clai do "calendar:create title:Client Call start:2025-10-16T10:00:00 duration:30 location:Zoom"

# Detailed event
clai do "calendar:create title:Project Review start:2025-10-17T15:00:00 duration:90 location:Conference Room A description:Quarterly review"
```

**Event output example:**
```
✅ Calendar event created successfully!

Event ID: abc123xyz
Title: Team Meeting
Start: 2025-10-15T14:00:00Z
End: 2025-10-15T15:00:00Z
Link: https://calendar.google.com/event?eid=...
```

#### List Calendar Events

View your upcoming calendar events:

```powershell
# List next 10 events (default)
clai do "calendar:list"

# List specific number of events
clai do "calendar:list next 5"
clai do "calendar:list next 20"
```

**Calendar output example:**
```
📅 Found 3 upcoming event(s):

================================================================================

1. Team Standup
   Start: 2025-10-15T09:00:00Z
   Location: Zoom
--------------------------------------------------------------------------------

2. Lunch with Client
   Start: 2025-10-15T12:00:00Z
   Location: Downtown Cafe
   Description: Discuss Q4 objectives...
--------------------------------------------------------------------------------

3. Project Review
   Start: 2025-10-17T15:00:00Z
   Location: Conference Room A
================================================================================
```

### History Commands

CloneAI automatically tracks your last 100 commands:

```powershell
# View all command history
clai history

# View last N commands
clai history --last 10
clai history --last 5

# Search command history
clai history --search "mail"
clai history --search "chat"

# Clear all history
clai clear-history
```

### Utility Commands

```powershell
# Navigate to CloneAI directory
clai-cd

# Reload CloneAI setup (if you make changes)
. $PROFILE

# Re-authenticate with Google APIs
clai reauth                    # Re-auth all services (Gmail + Calendar)
clai reauth gmail              # Re-auth Gmail only
clai reauth calendar           # Re-auth Calendar only
```

**When to use `clai reauth`:**
- After adding new scopes in Google Cloud Console
- Getting "insufficient authentication scopes" errors
- Want to switch Google accounts
- Troubleshooting authentication issues

The `reauth` command will:
1. Delete authentication tokens
2. Show which tokens were deleted
3. Provide clear next steps to complete re-authentication
```

---

## Troubleshooting

### General Issues

#### "clai: command not recognized"

**Solution 1**: Reload setup script
```powershell
. $PROFILE
```

**Solution 2**: Manually load CloneAI
```powershell
cd C:\Users\<YourUsername>\OneDrive\Documents\CloneAI
. .\setup-clai.ps1
```

**Solution 3**: Check if profile auto-load is set up
```powershell
Get-Content $PROFILE
```
Should contain: `. 'C:\Users\...\CloneAI\setup-clai.ps1'`

#### "Running scripts is disabled on this system"

**Solution**: Allow PowerShell to run scripts
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### "python: command not found"

**Solution**: Python not installed or not in PATH
1. Install Python from python.org
2. **CHECK** "Add Python to PATH" during installation
3. Restart PowerShell
4. Test: `python --version`

#### "Module not found: googleapiclient"

**Solution**: Install missing package
```powershell
pip install google-api-python-client google-auth-oauthlib
```

### Email Issues

#### "Credentials file not found"

**Solution**: Check credentials location
```powershell
# Check if file exists
Test-Path "$env:USERPROFILE\.clai\credentials.json"

# If False, you need to:
# 1. Complete Gmail API setup (see above)
# 2. Download credentials.json from Google Cloud Console
# 3. Move it to: C:\Users\<YourUsername>\.clai\credentials.json
```

#### "Access blocked: Authorization Error"

**Solution**: Add yourself as test user
1. Go to Google Cloud Console
2. "APIs & Services" > "OAuth consent screen"
3. Scroll to "Test users"
4. Click "Add Users"
5. Add your Gmail address
6. Save
7. Try authentication again

#### Email authentication not working

**Solution**: Delete token and re-authenticate
```powershell
Remove-Item "$env:USERPROFILE\.clai\token.pickle"
clai do "mail:list last 5"
```
Browser will open for fresh authentication.

#### "Wrong credentials type (Web App instead of Desktop App)"

**Solution**: Replace credentials
```powershell
# Create new Desktop App credentials in Google Cloud Console
# Download the new credentials.json, then:

# Backup old credentials
Copy-Item "$env:USERPROFILE\.clai\credentials.json" "$env:USERPROFILE\.clai\credentials.json.backup"

# Copy new credentials
Copy-Item "$env:USERPROFILE\Downloads\credentials.json" "$env:USERPROFILE\.clai\credentials.json" -Force

# Delete old token
Remove-Item "$env:USERPROFILE\.clai\token.pickle" -ErrorAction SilentlyContinue

# Re-authenticate
clai do "mail:list last 5"
```

### Virtual Environment Issues

#### Activation failed

**Solution**: Recreate virtual environment
```powershell
# Remove old venv
Remove-Item -Recurse -Force .venv

# Create new venv
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
pip install google-auth-oauthlib
```

---

## Command Reference

### Quick Command Lookup

| Command | Description |
|---------|-------------|
| `clai --help` | Show all available commands |
| `clai hi` | Interactive greeting |
| `clai chat "message"` | Direct chat with AI |
| `clai do "mail:list"` | List last 5 emails |
| `clai do "mail:list last 10"` | List last 10 emails |
| `clai do "mail:list email@domain.com"` | List emails from sender |
| `clai history` | View command history |
| `clai history --last 10` | View last 10 commands |
| `clai history --search "keyword"` | Search history |
| `clai clear-history` | Clear all history |
| `clai-cd` | Go to CloneAI directory |
| `. $PROFILE` | Reload PowerShell profile |

### Email Command Patterns

The email command format is flexible - all these work:

```powershell
# Basic
clai do "mail:list"
clai do "mail:list last 5"

# Count variations
clai do "mail:list last 10"
clai do "mail:list last 1"
clai do "mail:list last 100"

# Sender variations
clai do "mail:list john@example.com"
clai do "mail:list support@company.com"

# Combined (any order)
clai do "mail:list john@example.com last 3"
clai do "mail:list last 3 john@example.com"
clai do "mail:list last 10 support@github.com"
```

---

## Tips & Best Practices

### General Tips

1. **Always use quotes** for multi-word commands:
   ```powershell
   clai do "mail:list last 10"  # ✅ Correct
   clai do mail:list last 10     # ❌ Wrong
   ```

2. **Open new PowerShell window** to test auto-load:
   - Auto-load only runs when opening a new window
   - Existing windows need `. $PROFILE` to reload

3. **Check your history** to see what you've done:
   ```powershell
   clai history --last 10
   ```

4. **Navigate quickly** to CloneAI:
   ```powershell
   clai-cd  # Instantly jumps to CloneAI directory
   ```

5. **Use help frequently**:
   ```powershell
   clai --help           # All commands
   clai do --help        # Specific command help
   ```

### Security Tips

1. **Keep credentials private**:
   - Never share `credentials.json`
   - Never commit `token.pickle` to Git
   - Both files contain sensitive authentication data

2. **File locations**:
   ```
   C:\Users\<YourUsername>\.clai\
   ├── credentials.json    (OAuth credentials)
   ├── token.pickle       (Auth token - auto-generated)
   └── command_history.json (Command log - auto-generated)
   ```

3. **Add to .gitignore** if sharing code:
   ```
   .clai/
   credentials.json
   credentials1.json
   token.pickle
   ```

4. **Gmail access is read-only**:
   - CloneAI can only **read** your emails
   - It cannot send, delete, or modify emails
   - Scope: `gmail.readonly`

### Performance Tips

1. **Virtual environment**:
   - Always use the virtual environment
   - Keeps dependencies isolated
   - Prevents conflicts with other Python projects

2. **History management**:
   - Automatically keeps last 100 commands
   - Older commands are auto-deleted
   - Clear manually if needed: `clai clear-history`

3. **Token caching**:
   - Gmail token is cached for ~1 week
   - Re-authentication happens automatically
   - Delete token to force fresh auth

---

## File Locations Reference

### Project Files
```
C:\Users\<YourUsername>\OneDrive\Documents\CloneAI\
├── agent/
│   ├── cli.py                  # Main CLI interface
│   ├── tools/
│   │   ├── __init__.py
│   │   └── mail.py            # Email functionality
│   ├── state/
│   │   ├── __init__.py
│   │   └── logger.py          # Command logging
│   └── ...
├── docs/
│   └── COMPLETE_GUIDE.md      # This file!
├── .venv/                     # Virtual environment
├── setup-clai.ps1             # PowerShell setup script
├── requirements.txt           # Python dependencies
├── credentials.json           # (Optional) Your credentials backup
└── credentials1.json          # (Optional) Your credentials backup
```

### User Configuration Files
```
C:\Users\<YourUsername>\
├── OneDrive\Documents\PowerShell\
│   └── Microsoft.PowerShell_profile.ps1  # PowerShell profile
└── .clai\
    ├── credentials.json       # Gmail OAuth credentials
    ├── token.pickle          # Auth token (auto-generated)
    └── command_history.json  # Command log (auto-generated)
```

---

## What's Next?

### You're All Set! 🎉

You now have:
- ✅ CloneAI installed and working
- ✅ PowerShell auto-load configured
- ✅ Gmail API set up (if you completed that section)
- ✅ Full command reference

### Try These Commands

Start with the basics:
```powershell
# Say hello
clai hi

# Check some emails
clai do "mail:list last 5"

# View your history
clai history
```

### Explore More

- Add more tools to `agent/tools/`
- Customize commands in `agent/cli.py`
- Check `agent/state/logger.py` for history management
- Extend email functionality in `agent/tools/mail.py`

---

## Support & Documentation

### This Guide Covers Everything

This is your **complete guide** - it replaces these individual files:
- ~~GETTING_STARTED.md~~ ✓ Covered in "Installation" section
- ~~SETUP.md~~ ✓ Covered in "Installation" section
- ~~QUICKSTART.md~~ ✓ Covered in "Available Commands" section
- ~~GMAIL_SETUP.md~~ ✓ Covered in "Gmail API Setup" section
- ~~POWERSHELL_PROFILE_SETUP.md~~ ✓ Covered in "PowerShell Auto-Load" section

**You can safely delete those files** - everything is here!

### Need Help?

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [Command Reference](#command-reference)
3. Run `clai --help` for command list
4. Check your history: `clai history`

---

## Quick Reference Card

Print this section for easy reference:

```
╔══════════════════════════════════════════════════════════════════╗
║                    CloneAI Quick Reference                       ║
║            🌍 Cross-Platform: Windows • macOS • Linux            ║
╠══════════════════════════════════════════════════════════════════╣
║ INSTALLATION (Windows)                                           ║
║   python -m venv .venv                                           ║
║   .\.venv\Scripts\Activate.ps1                                   ║
║   pip install -r requirements.txt                                ║
║   pip install google-auth-oauthlib                               ║
║                                                                  ║
║ INSTALLATION (macOS/Linux)                                       ║
║   python3 -m venv .venv                                          ║
║   source .venv/bin/activate                                      ║
║   pip install -r requirements.txt                                ║
║   pip install google-auth-oauthlib                               ║
║                                                                  ║
║ AUTO-LOAD SETUP (Windows)                                        ║
║   Add-Content $PROFILE "`n. 'path\setup-clai.ps1'"              ║
║   . $PROFILE                                                     ║
║                                                                  ║
║ AUTO-LOAD SETUP (macOS/Linux)                                    ║
║   echo "source ~/Documents/CloneAI/setup-clai.sh" >> ~/.bashrc  ║
║   source ~/.bashrc    (or ~/.zshrc for Zsh)                      ║
║                                                                  ║
║ BASIC COMMANDS                                                   ║
║   clai hi              Interactive greeting                      ║
║   clai chat "msg"      Direct chat                               ║
║   clai --help          Show help                                 ║
║                                                                  ║
║ EMAIL COMMANDS                                                   ║
║   clai do "mail:list"                List emails                 ║
║   clai do "mail:list last 10"        Last 10 emails              ║
║   clai do "mail:drafts"              List drafts                 ║
║   clai do "mail:send to:x@test.com subject:Hi body:Hello"       ║
║   clai do "mail:send draft-id:abc123" Send draft                ║
║                                                                  ║
║ CALENDAR COMMANDS                                                ║
║   clai do "calendar:create title:Meeting start:2025-10-15T14:00 ║
║            :00 duration:60"                                      ║
║   clai do "calendar:list next 5"     Next 5 events               ║
║                                                                  ║
║ HISTORY                                                          ║
║   clai history                View all                           ║
║   clai history --last 10      Last 10                            ║
║   clai history --search "x"   Search                             ║
║   clai clear-history          Clear                              ║
║                                                                  ║
║ UTILITY COMMANDS                                                 ║
║   clai reload                 Reload CloneAI                     ║
║   clai reauth                 Re-authenticate (all)              ║
║   clai reauth gmail           Re-auth Gmail only                 ║
║   clai reauth calendar        Re-auth Calendar only              ║
║   clai-cd                     Go to CloneAI dir                  ║
║                                                                  ║
║ FILE LOCATIONS                                                   ║
║   ~/.clai/credentials.json         Google API credentials        ║
║   ~/.clai/token.pickle             Gmail auth token              ║
║   ~/.clai/token_calendar.pickle    Calendar auth token           ║
║   ~/.clai/command_history.json     Command log                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

**That's it! You're now ready to use CloneAI. Happy automating! 🚀**
