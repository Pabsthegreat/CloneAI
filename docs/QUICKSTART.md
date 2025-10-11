# CloneAI - Quick Start Guide

## 🚀 Getting Started

### 1. Load CloneAI in PowerShell
```powershell
cd C:\Users\adars\OneDrive\Documents\CloneAI
. .\setup-clai.ps1
```

### 2. Available Commands

#### Basic Commands
```powershell
# Interactive greeting
clai hi

# Chat with the agent
clai chat "help me organize my tasks"

# Get help
clai --help
clai do --help
```

#### Email Commands

**List last 5 emails (default):**
```powershell
clai do "mail:list"
clai do "mail:list last 5"
```

**List last N emails:**
```powershell
clai do "mail:list last 10"
clai do "mail:list last 20"
```

**List emails from specific sender:**
```powershell
clai do "mail:list xyz@gmail.com"
clai do "mail:list support@github.com"
```

**Combine filters:**
```powershell
clai do "mail:list xyz@gmail.com last 3"
clai do "mail:list last 3 xyz@gmail.com"
```

## ⚙️ First-Time Setup

### For Email Features

1. **Set up Gmail API credentials** (one-time setup)
   - Follow instructions in: [`docs/GMAIL_SETUP.md`](docs/GMAIL_SETUP.md)
   - Download `credentials.json` from Google Cloud Console
   - Place it in: `C:\Users\<YourUsername>\.clai\credentials.json`

2. **First authentication:**
   ```powershell
   clai do "mail:list last 5"
   ```
   - Opens browser for Google sign-in
   - Grant permissions
   - Token saved for future use

## 📂 File Structure

```
CloneAI/
├── agent/
│   ├── cli.py           # Main CLI interface
│   ├── tools/
│   │   └── mail.py      # Email functionality
│   └── ...
├── docs/
│   ├── GMAIL_SETUP.md   # Detailed Gmail setup guide
│   └── ...
├── setup-clai.ps1       # PowerShell setup script
├── clai.ps1             # CLI wrapper
└── requirements.txt     # Python dependencies
```

## 🐛 Troubleshooting

### "clai: command not recognized"
```powershell
# Reload the setup script
. .\setup-clai.ps1
```

### Email authentication errors
- See [`docs/GMAIL_SETUP.md`](docs/GMAIL_SETUP.md)
- Delete token and re-authenticate:
  ```powershell
  Remove-Item "$env:USERPROFILE\.clai\token.pickle"
  clai do "mail:list last 5"
  ```

## 🔮 Coming Soon

- [ ] Send emails
- [ ] Search emails with advanced queries
- [ ] Calendar integration
- [ ] Task management
- [ ] File operations

## 💡 Tips

1. **Use quotes** for multi-word commands:
   ```powershell
   clai do "mail:list last 10"  # ✅ Correct
   clai do mail:list last 10     # ❌ Wrong (no quotes)
   ```

2. **Reload after code changes:**
   ```powershell
   . .\setup-clai.ps1  # Reloads the clai function
   ```

3. **Check command syntax:**
   ```powershell
   clai --help        # List all commands
   clai do --help     # Help for 'do' command
   ```

## 📝 Examples

### Example 1: Check recent emails
```powershell
clai do "mail:list last 5"
```

### Example 2: Find emails from your boss
```powershell
clai do "mail:list boss@company.com"
```

### Example 3: Interactive conversation
```powershell
clai hi
# Then type: organize my inbox
```

## 🆘 Need Help?

1. Check [`docs/GMAIL_SETUP.md`](docs/GMAIL_SETUP.md) for Gmail setup
2. Run `clai --help` for command reference
3. Check error messages for specific guidance
