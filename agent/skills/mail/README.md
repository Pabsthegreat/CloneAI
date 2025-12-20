# Mail Skill (`agent/skills/mail/`)

This module handles all email-related functionality.

## Key Files

*   `client.py`: **Gmail Client**. Handles authentication (OAuth) and Gmail API calls (list, send, draft).
*   `workflows.py`: **Command Definitions**. Defines commands like `mail:list`, `mail:send`, `mail:draft`.
*   `parser.py`: **Email Parser**. Utilities for extracting information (like meetings) from email bodies.

## Capabilities

*   List emails (with filtering).
*   Draft and send emails.
*   Summarize emails (via LLM).
*   Extract meeting invites from emails.
