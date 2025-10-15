"""
General notes and guidelines for CloneAI commands.

All commands are now automatically registered via @register_workflow decorators.
No manual catalog updates needed!
"""

from __future__ import annotations

# General command format notes and examples for LLM prompts
LEGACY_NOTES = """IMPORTANT NOTES:
- Message IDs are hexadecimal strings (e.g., 199abc123def)
- Datetime format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-10-15T14:00:00)
- Time format for tasks: HH:MM (24-hour, e.g., 09:00, 14:30)
- Duration in minutes (e.g., 60 for 1 hour, 30 for 30 minutes)
- Multiple attachments: comma-separated paths (no spaces)
- If user says "last 5 emails", use "mail:list last 5"
- If user mentions downloading attachments, they need to provide the message ID
- For meeting requests with participant email(s), prefer mail:invite; otherwise use calendar:create

EXAMPLES:
- "show me my last 10 emails" → mail:list last 10
- "list emails from john@example.com" → mail:list sender:john@example.com
- "download attachments from message 199abc123" → mail:download id:199abc123
- "create a meeting called Team Sync on Oct 15 at 2pm for 1 hour" → calendar:create title:Team Sync start:2025-10-15T14:00:00 duration:60
- "show my next 5 calendar events" → calendar:list next 5
- "send email to bob@test.com with subject Hello and body Hi there" → mail:send to:bob@test.com subject:Hello body:Hi there

CRITICAL MEETING RULES:
- If the user mentions scheduling/creating a meeting WITH another person's email → use mail:invite (sends email invitation)
- If the user only wants to add to their own calendar (no email mentioned) → use calendar:create
- mail:invite requires: to:EMAIL, subject:TEXT, time:DATETIME, duration:MINS
- Example: "schedule meeting with john@test.com" → mail:invite to:john@test.com subject:Meeting time:2025-10-15T14:00:00 duration:60
- Example: "add to my calendar" → calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60
"""

__all__ = ["LEGACY_SECTIONS", "LEGACY_NOTES"]
