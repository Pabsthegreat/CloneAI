# CloneAI - Your Personal CLI Agent

A local, permissioned personal assistant that runs in your command line. Check emails, chat with AI, and automate tasks - all from your terminal!

**🌍 Cross-Platform Support:** Works on Windows, macOS (including Apple Silicon), and Linux!

## � Complete Documentation

**👉 [READ THE COMPLETE GUIDE](docs/COMPLETE_GUIDE.md)** - Everything you need in one place!

This comprehensive guide covers:
- ✅ Installation & setup
- ✅ PowerShell auto-load configuration
- ✅ Gmail API setup for email features
- ✅ All available commands
- ✅ Complete troubleshooting guide
- ✅ Quick reference card

### Quick Install

**Windows (PowerShell):**
```powershell
cd C:\Users\<YourUsername>\OneDrive\Documents\CloneAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install google-auth-oauthlib
.\setup-clai.ps1
```

**macOS/Linux (Bash/Zsh):**
```bash
cd ~/Documents/CloneAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install google-auth-oauthlib
chmod +x setup-clai.sh
echo "source ~/Documents/CloneAI/setup-clai.sh" >> ~/.bashrc  # or ~/.zshrc for Zsh
source ~/.bashrc  # or source ~/.zshrc for Zsh
```

**After setup:**
- **Windows:** Restart your PowerShell terminal or run: `$env:Path = [System.Environment]::GetEnvironmentVariable('Path','User') + ';' + [System.Environment]::GetEnvironmentVariable('Path','Machine')`
- **macOS/Linux:** Open a new terminal (the setup is already done!)

Then test from **any directory**: `clai hi`

✨ **The venv activates automatically!** No need to manually activate it before using `clai`.

CloneAI will automatically detect your system and display: `System: Windows (x86_64)`, `System: macOS Silicon`, or `System: Linux (x86_64)`

## ✨ Features

- 🤖 **Natural Language Commands** - Use plain English to control CloneAI (powered by Ollama)
  - 🗣️ **Interpret Mode** - Convert natural language to commands: `clai interpret "show my emails"`
  - ✍️ **AI Email Drafting** - Generate professional emails: `clai draft-email "write to john@example.com"`
  - � **Multi-Step Workflows** - Automate email replies: `clai auto "check my last 3 emails and reply"`
- �📧 **Email Management** - List, search, create drafts, send emails with attachments
  - 🎯 **Priority Email Buckets** - Filter emails from important senders/domains
  - 👁️ **View Full Emails** - See complete email body and content
  - 📎 **Download Attachments** - Save email attachments to disk
  - 🤖 **Batch Reply** - AI-powered professional replies to multiple emails at once
- 📅 **Calendar Integration** - Create and list Google Calendar events
  - 🔍 **Auto-Meeting Detection** - Scan emails for meeting invites and add to calendar
  - 📨 **Send Meeting Invites** - Create and send meeting invitations with links
- ⏰ **Task Scheduler** - Run commands automatically at specific times daily
- 🔗 **Cascading Commands** - Chain multiple commands with `&&`
- 📄 **Document Utilities** - Merge PDFs/PPTs, convert between formats (PDF↔DOCX, PPT→PDF)
- 💬 **AI Chat** - Interactive conversations with your assistant  
- 📝 **Command History** - Automatically tracks last 100 commands
- 🔧 **Extensible** - Easy to add new tools and integrations
- 🔒 **Private** - Runs locally on your machine (requires Ollama for AI features)

## � Documentation Files

- **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** - 📖 **START HERE!** All-in-one setup & usage guide
- [EMAIL_IMPLEMENTATION.md](docs/EMAIL_IMPLEMENTATION.md) - Technical details for developers
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design documentation
- [SECURITY.md](docs/SECURITY.md) - Security guidelines
- [TESTING.md](docs/TESTING.md) - Testing procedures

## 🎯 Example Commands

```bash
# Natural Language & AI Features (requires Ollama)
clai interpret "show me my last 5 emails"              # Parse natural language
clai interpret --run "list emails from john@example.com"  # Auto-execute
clai draft-email "write to sarah@company.com about the meeting"  # AI email generation
clai auto "check my last 3 emails and reply to them"   # Automated workflow

# Basic interaction
clai hi                              # Interactive greeting
clai chat "help me organize tasks"   # Direct chat

# Email features
clai do "mail:list last 5"           # Recent emails
clai do "mail:view id:MESSAGE_ID"    # View full email
clai do "mail:download id:MSG_ID"    # Download attachments
clai do "mail:priority last 10"      # Priority emails
clai do "mail:scan-meetings"         # Scan for meeting invites
clai do "mail:add-meeting email-id:MSG_ID"  # Add to calendar

# Priority email management
clai do "mail:priority-add boss@company.com"    # Add priority sender
clai do "mail:priority-add @company.com"        # Add priority domain

# Calendar features
clai do "calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60"
clai do "calendar:list next 5"       # Next 5 events
clai do "mail:invite to:user@test.com subject:Sync time:2025-10-15T14:00:00"

# Scheduled tasks
clai do "task:add name:Check Email command:mail:priority time:09:00"
clai do "tasks"                      # List all tasks
clai scheduler start                 # Start scheduler daemon

# Cascading commands
clai do "mail:priority && mail:scan-meetings && calendar:list"

# Document utilities
clai merge pdf                       # Merge multiple PDFs
clai merge ppt                       # Merge multiple PowerPoints
clai convert pdf-to-docx             # Convert PDF to Word

# Command history
clai history                         # View history
clai history --search "mail"         # Search history

# Re-authenticate Google APIs
clai reauth                          # Re-auth all services
clai reauth gmail                    # Re-auth Gmail only
```

## 🛠️ Requirements

- Python 3.10 or higher
- **Windows:** PowerShell 5.1+ or PowerShell Core 7+
- **macOS/Linux:** Bash, Zsh, or Fish shell
- Gmail API credentials (for email features)
- Internet connection for Google API authentication

## 📂 Project Structure

```
CloneAI/
├── agent/
│   ├── cli.py           # Main CLI interface
│   ├── tools/           # Email and other tools
│   └── state/           # Command logging
├── docs/                # All documentation
├── setup-clai.ps1       # PowerShell setup
└── requirements.txt     # Python dependencies
``` (full README.md content)