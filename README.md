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
Add-Content $PROFILE "`n# CloneAI Auto-Load`n. 'C:\Users\<YourUsername>\OneDrive\Documents\CloneAI\setup-clai.ps1'"
. $PROFILE
```

**macOS/Linux (Bash/Zsh):**
```bash
cd ~/Documents/CloneAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install google-auth-oauthlib
echo "source ~/Documents/CloneAI/setup-clai.sh" >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or ~/.zshrc
```

Then test: `clai --help`

CloneAI will automatically detect your system and display: `System: Windows (x86_64)`, `System: macOS Silicon`, or `System: Linux (x86_64)`

## ✨ Features

- 📧 **Email Management** - List, search, and create Gmail drafts
- 📅 **Calendar Integration** - Create and list Google Calendar events
- 💬 **AI Chat** - Interactive conversations with your assistant  
- 📝 **Command History** - Automatically tracks last 100 commands
- 🔧 **Extensible** - Easy to add new tools and integrations
- 🔒 **Private** - Runs locally on your machine

## � Documentation Files

- **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** - 📖 **START HERE!** All-in-one setup & usage guide
- [EMAIL_IMPLEMENTATION.md](docs/EMAIL_IMPLEMENTATION.md) - Technical details for developers
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design documentation
- [SECURITY.md](docs/SECURITY.md) - Security guidelines
- [TESTING.md](docs/TESTING.md) - Testing procedures

## 🎯 Example Commands

```powershell
# Basic interaction
clai hi                              # Interactive greeting
clai chat "help me organize tasks"   # Direct chat

# Email features
clai do "mail:list last 5"           # Recent emails
clai do "mail:list boss@work.com"    # From specific sender
clai do "mail:draft to:user@test.com subject:Hello body:Hi there"

# Calendar features
clai do "calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60"
clai do "calendar:list next 5"       # Next 5 events

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