# Fresh Computer Setup Guide

Complete setup instructions for the Agent Workflow project on a new Windows machine.

---

## 1. Install VS Code

Download and install from: https://code.visualstudio.com/download

---

## 2. Install Python 3.12

Download from: https://www.python.org/downloads/

During installation:
- Check "Add Python to PATH"
- Check "Install for all users" (optional)

Verify installation:
```powershell
python --version
```

---

## 3. Install Git

Download from: https://git-scm.com/download/win

Or via winget:
```powershell
winget install Git.Git
```

---

## 4. Install Node.js (required for Claude Code)

Download from: https://nodejs.org/ (LTS version)

Or via winget:
```powershell
winget install OpenJS.NodeJS.LTS
```

---

## 5. Install Claude Code CLI

```powershell
npm install -g @anthropic-ai/claude-code
```

Verify installation:
```powershell
claude --version
```

---

## 6. Install Python Dependencies

```powershell
pip install modal
```

---

## 7. Setup Modal

Run the setup command (will open browser for authentication):
```powershell
python -m modal setup
```

**Important for Windows**: Always run Modal commands with UTF-8 encoding to avoid character errors:
```powershell
$env:PYTHONUTF8=1; python -m modal run <script.py>
```

Or in bash/git bash:
```bash
PYTHONUTF8=1 python -m modal run <script.py>
```

### Create Modal Secrets

Create the Slack webhook secret:
```powershell
$env:PYTHONUTF8=1; python -m modal secret create slack-webhook SLACK_WEBHOOK_URL=<your-webhook-url>
```

---

## 8. Configure Environment Variables

Create a `.env` file in the project root with:

```env
# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_USERNAME=Claude Agent
SLACK_ENABLED=true
```

Get your Slack webhook URL at: https://api.slack.com/messaging/webhooks

---

## 9. Claude Code Global Settings

Create/edit `~/.claude/settings.json` (C:\Users\<username>\.claude\settings.json):

```json
{
  "enabledPlugins": {
    "frontend-design@claude-plugins-official": true,
    "backend-development@claude-code-workflows": true,
    "database-design@claude-code-workflows": true,
    "supabase@claude-plugins-official": true,
    "vercel@claude-plugins-official": true
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -Command \"(New-Object Media.SoundPlayer 'C:\\Windows\\Media\\tada.wav').PlaySync()\""
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -Command \"(New-Object Media.SoundPlayer 'C:\\Windows\\Media\\ringout.wav').PlaySync()\""
          }
        ]
      }
    ]
  }
}
```

---

## 10. Claude Code Project Settings

Create `.claude/settings.local.json` in the project folder:

```json
{
  "permissions": {
    "allow": [
      "Bash(mkdir:*)",
      "Bash(git:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(PYTHONUTF8=1 python -m modal:*)"
    ]
  },
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -Command \"(New-Object Media.SoundPlayer 'C:\\Windows\\Media\\Windows Notify System Generic.wav').PlaySync()\""
          }
        ]
      }
    ]
  }
}
```

---

## 11. Clone the Project

```powershell
git clone <your-repo-url>
cd "Agent Workflow"
```

---

## Quick Reference Commands

### Modal Commands (always use PYTHONUTF8=1 on Windows)

```powershell
# Run a Modal script
$env:PYTHONUTF8=1; python -m modal run script.py

# Deploy a scheduled function
$env:PYTHONUTF8=1; python -m modal deploy script.py

# Stop a deployed app
$env:PYTHONUTF8=1; python -m modal app stop app-name

# List deployed apps
$env:PYTHONUTF8=1; python -m modal app list

# Create a secret
$env:PYTHONUTF8=1; python -m modal secret create secret-name KEY=value
```

### Test Slack Notifications

```powershell
python execution/slack_notifier.py
```

---

## Project Structure

```
Agent Workflow/
├── .claude/
│   └── settings.local.json    # Claude Code project settings
├── .env                        # Environment variables (not in git)
├── execution/
│   ├── env_loader.py          # Loads .env file
│   ├── slack_notifier.py      # Slack notification utilities
│   └── observability.py       # Observability helpers
├── modal_slack_scheduler.py   # Modal scheduled Slack task
└── SETUP.md                   # This file
```

---

## Troubleshooting

### Modal Unicode Errors on Windows
If you see `'charmap' codec can't encode character` errors, ensure you're using:
```powershell
$env:PYTHONUTF8=1
```

### Claude Code not found
Ensure Node.js bin directory is in your PATH, then reinstall:
```powershell
npm install -g @anthropic-ai/claude-code
```

### Python not found
Reinstall Python with "Add to PATH" checked, or manually add to PATH:
```
C:\Users\<username>\AppData\Local\Programs\Python\Python312\
C:\Users\<username>\AppData\Local\Programs\Python\Python312\Scripts\
```
