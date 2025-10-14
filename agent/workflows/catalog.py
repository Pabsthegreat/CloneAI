"""Legacy command catalog used until all commands are migrated to workflows."""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, List, Tuple

# (usage, description)
LEGACY_SECTIONS: Dict[str, List[Tuple[str, str]]] = OrderedDict(
    {
        "EMAIL COMMANDS": [
            ("mail:view id:MESSAGE_ID", "View full email content"),
            (
                "mail:download id:MESSAGE_ID [dir:PATH]",
                "Download email attachments",
            ),
            (
                "mail:draft to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL] [attachment:PATH]",
                "Create draft email",
            ),
            (
                "mail:reply id:MESSAGE_ID [body:TEXT]",
                "Reply to an email (AI generates body if not provided)",
            ),
            (
                "mail:send to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL] [attachments:PATHS]",
                "Send email immediately",
            ),
            ("mail:send draft-id:DRAFT_ID", "Send an existing draft"),
            ("mail:drafts [last N]", "List draft emails"),
            ("mail:priority [last N]", "List priority emails"),
            ("mail:priority-add EMAIL|@DOMAIN", "Add priority sender"),
            ("mail:priority-remove EMAIL|@DOMAIN", "Remove priority sender"),
            ("mail:priority-list", "Show priority configuration"),
            ("mail:scan-meetings [hours:N]", "Scan for meeting invitations"),
            (
                "mail:add-meeting email-id:MSG_ID [time:DATETIME]",
                "Add meeting invite from email to calendar",
            ),
            (
                "mail:invite to:EMAIL subject:TEXT time:DATETIME duration:MINS [platform:TEXT]",
                "Send meeting invite to participants",
            ),
        ],
        "CALENDAR COMMANDS": [
            (
                "calendar:create title:TEXT start:DATETIME [end:DATETIME|duration:MINS] [location:TEXT] [description:TEXT]",
                "Create calendar event",
            ),
            ("calendar:list [next N]", "List upcoming events"),
        ],
        "SCHEDULER COMMANDS": [
            ("tasks", "List all scheduled tasks"),
            ("task:add name:TEXT command:COMMAND time:HH:MM", "Add scheduled task"),
            ("task:remove TASK_ID", "Remove scheduled task"),
            ("task:toggle TASK_ID", "Enable/disable scheduled task"),
        ],
        "DOCUMENT COMMANDS": [
            ("doc:merge-pdf files:FILE1,FILE2,... output:OUTPUT_FILE", "Merge multiple PDF files"),
            ("merge ppt", "Interactive PowerPoint merge"),
            ("convert pdf-to-docx", "Convert PDF to Word"),
            ("convert docx-to-pdf", "Convert Word to PDF (Windows only)"),
            ("convert ppt-to-pdf", "Convert PPT to PDF (Windows only)"),
        ],
        "CASCADING COMMANDS": [
            ("COMMAND1 && COMMAND2 && COMMAND3", "Chain multiple commands"),
        ],
        "GENERAL COMMANDS": [
            ("hi", "Interactive greeting"),
            ("chat \"message\"", "Chat with CloneAI"),
            ("history", "Show recent command history"),
            ("history --search QUERY", "Search command history"),
            ("reauth [service]", "Reauthenticate integrations"),
        ],
    }
)

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
