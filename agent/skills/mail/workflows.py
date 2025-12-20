"""Mail-related workflows registered with the workflow registry."""

from __future__ import annotations

import re
import shlex
from typing import Any, Dict, Optional, List

from .client import (
    get_email_messages,
    format_email_list,
    get_full_email,
    create_draft_email,
    list_drafts_emails,
    send_email_now,
    send_draft_email,
    download_email_attachments,
    GmailClient,
    scan_emails_for_meetings,
    add_meeting_from_email,
    create_and_send_meeting_invite,
)
from .priority import (
    get_priority_emails,
    add_priority_sender,
    remove_priority_sender,
    list_priority_senders,
)
from agent.workflows import ParameterSpec, WorkflowContext, WorkflowValidationError, register_workflow

_EMAIL_REGEX = re.compile(
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
)


def _parse_mail_list(raw_args: str, _spec: Any) -> Dict[str, Any]:
    """
    Parse arguments for mail:list command.

    Supports:
        - "last N" syntax (e.g., "last 5")
        - sender email in free text or explicit "sender:" field
        - explicit "count:" override
    """
    arguments: Dict[str, Any] = {"count": 5, "sender": None, "query": None}

    if not raw_args:
        return arguments

    last_match = re.search(r"last\s+(\d+)", raw_args, re.IGNORECASE)
    if last_match:
        arguments["count"] = int(last_match.group(1))

    email_match = _EMAIL_REGEX.search(raw_args)
    if email_match:
        arguments["sender"] = email_match.group(1)

    for token in shlex.split(raw_args):
        if ":" in token:
            key, value = token.split(":", 1)
        elif "=" in token:
            key, value = token.split("=", 1)
        else:
            continue

        key_lower = key.lower().strip("-")
        if key_lower in {"count", "max", "limit"}:
            try:
                arguments["count"] = int(value)
            except ValueError as exc:
                raise WorkflowValidationError(
                    f"Invalid count value '{value}'. Expected an integer."
                ) from exc
        elif key_lower in {"sender", "from"}:
            arguments["sender"] = value
        elif key_lower == "query":
            arguments["query"] = value

    return arguments


@register_workflow(
    namespace="mail",
    name="list",
    summary="List recent emails from primary inbox.",
    description="Fetches recent emails from Gmail primary inbox, optionally filtered by sender.",
    parameters=(
        ParameterSpec(
            name="count",
            description="Number of emails to retrieve.",
            type=int,
            default=10,
        ),
        ParameterSpec(
            name="sender",
            description="Filter emails by sender address.",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="query",
            description="Additional Gmail query string.",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="category",
            description="Gmail category (primary, social, promotions, updates, forums). Defaults to primary.",
            type=str,
            default="primary",
        ),
    ),
    parameter_parser=_parse_mail_list,
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:list [last N] [sender:EMAIL] [query:QUERY] [category:CATEGORY]",
        "returns": "str",
        "examples": [
            'mail:list last 10',
            'mail:list sender:boss@example.com',
            'mail:list category:primary',
        ],
    },
)
def run_mail_list_workflow(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing emails from primary inbox."""
    count = params.get("count", 10)
    sender = params.get("sender")
    query = params.get("query")
    category = params.get("category", "primary")  # Default to primary inbox

    messages = get_email_messages(count=count, sender=sender, query=query, category=category)
    formatted = format_email_list(messages)

    extras = ctx.extras
    if extras is not None:
        extras.setdefault("workflow", "mail:list")
        extras.setdefault("parameters", {})
        extras["parameters"].update(
            {"count": count, "sender": sender, "query": query}
        )
        extras["mail:last_messages"] = messages
        extras["mail:last_message_ids"] = [msg["id"] for msg in messages]

    return formatted


# ============================================================================
# mail:view - View full email content
# ============================================================================

@register_workflow(
    namespace="mail",
    name="view",
    summary="View full email content",
    description="Retrieves and displays the full content of an email by message ID.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Message ID of the email to view",
            type=str,
            required=True,
            aliases=["message_id", "msg_id"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:view id:MESSAGE_ID",
        "returns": "str",
        "examples": ["mail:view id:199e610074e62292"],
    },
)
def mail_view_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for viewing email content."""
    message_id = params.get("id")
    if not message_id:
        raise WorkflowValidationError("Message ID is required")
    
    return get_full_email(message_id)


# ============================================================================
# mail:download - Download email attachments
# ============================================================================

@register_workflow(
    namespace="mail",
    name="download",
    summary="Download email attachments",
    description="Downloads all attachments from an email to a specified directory.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Message ID of the email",
            type=str,
            required=True,
            aliases=["message_id", "msg_id"]
        ),
        ParameterSpec(
            name="dir",
            description="Directory to save attachments (optional)",
            type=str,
            default=None,
            aliases=["directory", "path"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:download id:MESSAGE_ID [dir:PATH]",
        "returns": "str",
        "examples": [
            "mail:download id:199e610074e62292",
            "mail:download id:199e610074e62292 dir:~/Downloads"
        ],
    },
)
def mail_download_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for downloading attachments."""
    message_id = params.get("id")
    save_dir = params.get("dir")
    
    if not message_id:
        raise WorkflowValidationError("Message ID is required")
    
    return download_email_attachments(message_id, save_dir)


# ============================================================================
# mail:draft - Create draft email
# ============================================================================

@register_workflow(
    namespace="mail",
    name="draft",
    summary="Create draft email",
    description="Creates a draft email with optional AI-generated body if not provided.",
    parameters=(
        ParameterSpec(
            name="to",
            description="Recipient email address",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="subject",
            description="Email subject",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="body",
            description="Email body (AI generates if not provided)",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="cc",
            description="CC email address",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="bcc",
            description="BCC email address",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="attachments",
            description="Comma-separated attachment file paths",
            type=str,
            default=None,
            aliases=["attachment"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:draft to:EMAIL subject:TEXT [body:TEXT] [cc:EMAIL] [bcc:EMAIL] [attachments:PATHS]",
        "returns": "str",
        "examples": [
            "mail:draft to:user@test.com subject:Hello body:Hi there",
            "mail:draft to:user@test.com subject:Meeting attachments:doc.pdf"
        ],
    },
)
def mail_draft_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for creating draft emails."""
    to = params.get("to")
    subject = params.get("subject")
    body = params.get("body")
    cc = params.get("cc")
    bcc = params.get("bcc")
    attachments_str = params.get("attachments")
    
    if not to or not subject:
        raise WorkflowValidationError("'to' and 'subject' are required")
    
    # Parse attachments
    attachments = None
    if attachments_str:
        attachments = [path.strip() for path in attachments_str.split(',')]
    
    # Generate body if not provided
    if not body:
        from agent.tools.nl_parser import generate_email_content
        instruction = f"write email to {to} about {subject}"
        if attachments:
            attachment_names = ", ".join([att.split('/')[-1] for att in attachments])
            instruction += f". Mention that attachments ({attachment_names}) are included."
        
        email_gen = generate_email_content(instruction)
        if email_gen.get("success"):
            body = email_gen.get("body", "")
    
    result = create_draft_email(to, subject, body or "", cc, bcc, attachments)
    
    # Store draft ID in context if available
    if ctx.extras is not None:
        draft_id_match = re.search(r"Draft ID:\s*([^\s]+)", result)
        if draft_id_match:
            ctx.extras["mail:last_draft_ids"] = [draft_id_match.group(1)]
    
    return result


# ============================================================================
# mail:reply - Reply to email
# ============================================================================

@register_workflow(
    namespace="mail",
    name="reply",
    summary="Reply to an email",
    description="Replies to an email with optional AI-generated body.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Message ID to reply to",
            type=str,
            required=True,
            aliases=["message_id", "msg_id"]
        ),
        ParameterSpec(
            name="body",
            description="Reply body (AI generates if not provided)",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:reply id:MESSAGE_ID [body:TEXT]",
        "returns": "str",
        "examples": [
            "mail:reply id:199e610074e62292",
            "mail:reply id:199e610074e62292 body:Thanks for the update!"
        ],
    },
)
def mail_reply_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for replying to emails."""
    message_id = params.get("id")
    body = params.get("body")
    
    if not message_id:
        raise WorkflowValidationError("Message ID is required")
    
    # Get the original email
    client = GmailClient()
    original_email = client.get_full_message(message_id)
    
    if not original_email:
        return f"❌ Email not found: {message_id}"
    
    # Extract original sender and subject
    original_from = original_email.get('from', '')
    original_subject = original_email.get('subject', '')
    original_body = original_email.get('body', '')
    
    # Create reply subject (add "Re:" if not present)
    reply_subject = original_subject if original_subject.startswith('Re:') else f"Re: {original_subject}"
    
    # Generate or use provided body
    if not body:
        # Use AI to generate reply
        from agent.tools.nl_parser import generate_email_content
        instruction = f"write a professional reply to email from {original_from} with subject '{original_subject}'. Original message: {original_body[:500]}"
        generated = generate_email_content(instruction, user_context=f"This is a reply to: {original_body[:200]}")
        
        if generated.get("success"):
            body = generated["body"]
        else:
            return "❌ Failed to generate reply. Please provide body manually."
    
    # Create draft reply
    result = create_draft_email(
        to=original_from,
        subject=reply_subject,
        body=body
    )
    
    # Store draft ID in context if available
    if ctx.extras is not None:
        draft_id_match = re.search(r"Draft ID:\s*([^\s]+)", result)
        if draft_id_match:
            ctx.extras["mail:last_draft_ids"] = [draft_id_match.group(1)]
    
    return result


# ============================================================================
# mail:send - Send email immediately
# ============================================================================

@register_workflow(
    namespace="mail",
    name="send",
    summary="Send email immediately",
    description="Sends an email immediately or sends an existing draft.",
    parameters=(
        ParameterSpec(
            name="to",
            description="Recipient email address",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="subject",
            description="Email subject",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="body",
            description="Email body",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="cc",
            description="CC email address",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="bcc",
            description="BCC email address",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="attachments",
            description="Comma-separated attachment file paths",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="draft_id",
            description="Draft ID to send (alternative to composing new email)",
            type=str,
            default=None,
            aliases=["draft-id", "draftid"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:send to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL] [attachments:PATHS] OR mail:send draft-id:DRAFT_ID",
        "returns": "str",
        "examples": [
            "mail:send to:user@test.com subject:Hello body:Hi there",
            "mail:send draft-id:r-123456789"
        ],
    },
)
def mail_send_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for sending emails."""
    draft_id = params.get("draft_id")
    
    # If draft_id provided, send that draft
    if draft_id:
        return send_draft_email(draft_id)
    
    # Otherwise send new email
    to = params.get("to")
    subject = params.get("subject")
    body = params.get("body")
    cc = params.get("cc")
    bcc = params.get("bcc")
    attachments_str = params.get("attachments")
    
    if not to or not subject or not body:
        raise WorkflowValidationError("'to', 'subject', and 'body' are required (or provide draft-id)")
    
    # Parse attachments
    attachments = None
    if attachments_str:
        attachments = [path.strip() for path in attachments_str.split(',')]
    
    return send_email_now(to, subject, body, cc, bcc, attachments)


# ============================================================================
# mail:drafts - List draft emails
# ============================================================================

@register_workflow(
    namespace="mail",
    name="drafts",
    summary="List draft emails",
    description="Lists all draft emails in the inbox.",
    parameters=(
        ParameterSpec(
            name="last",
            description="Number of drafts to list",
            type=int,
            default=10,
            aliases=["count", "max"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:drafts [last N]",
        "returns": "str",
        "examples": ["mail:drafts", "mail:drafts last 5"],
    },
)
def mail_drafts_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing drafts."""
    count = params.get("last", 10)
    return list_drafts_emails(count)


# ============================================================================
# mail:priority - List priority emails
# ============================================================================

@register_workflow(
    namespace="mail",
    name="priority",
    summary="List priority emails",
    description="Lists emails from priority senders.",
    parameters=(
        ParameterSpec(
            name="last",
            description="Number of priority emails to list",
            type=int,
            default=10,
            aliases=["count", "max"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:priority [last N]",
        "returns": "str",
        "examples": ["mail:priority", "mail:priority last 5"],
    },
)
def mail_priority_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing priority emails."""
    count = params.get("last", 10)
    return get_priority_emails(count)


# ============================================================================
# mail:priority-add - Add priority sender
# ============================================================================

@register_workflow(
    namespace="mail",
    name="priority-add",
    summary="Add priority sender",
    description="Adds an email address or domain to the priority senders list.",
    parameters=(
        ParameterSpec(
            name="identifier",
            description="Email address or @domain to add",
            type=str,
            required=True,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:priority-add EMAIL|@DOMAIN",
        "returns": "str",
        "examples": [
            "mail:priority-add boss@company.com",
            "mail:priority-add @important-domain.com"
        ],
    },
)
def mail_priority_add_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for adding priority senders."""
    identifier = params.get("identifier")
    if not identifier:
        raise WorkflowValidationError("Email or domain identifier is required")
    return add_priority_sender(identifier)


# ============================================================================
# mail:priority-remove - Remove priority sender
# ============================================================================

@register_workflow(
    namespace="mail",
    name="priority-remove",
    summary="Remove priority sender",
    description="Removes an email address or domain from the priority senders list.",
    parameters=(
        ParameterSpec(
            name="identifier",
            description="Email address or @domain to remove",
            type=str,
            required=True,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:priority-remove EMAIL|@DOMAIN",
        "returns": "str",
        "examples": [
            "mail:priority-remove boss@company.com",
            "mail:priority-remove @important-domain.com"
        ],
    },
)
def mail_priority_remove_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for removing priority senders."""
    identifier = params.get("identifier")
    if not identifier:
        raise WorkflowValidationError("Email or domain identifier is required")
    return remove_priority_sender(identifier)


# ============================================================================
# mail:priority-list - List priority senders
# ============================================================================

@register_workflow(
    namespace="mail",
    name="priority-list",
    summary="Show priority configuration",
    description="Lists all configured priority senders.",
    parameters=(),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:priority-list",
        "returns": "str",
        "examples": ["mail:priority-list"],
    },
)
def mail_priority_list_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing priority senders."""
    return list_priority_senders()


# ============================================================================
# mail:scan-meetings - Scan for meeting invitations
# ============================================================================

@register_workflow(
    namespace="mail",
    name="scan-meetings",
    summary="Scan for meeting invitations",
    description="Scans recent emails for meeting invitations.",
    parameters=(
        ParameterSpec(
            name="hours",
            description="Number of hours to look back",
            type=int,
            default=24,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:scan-meetings [hours:N]",
        "returns": "str",
        "examples": ["mail:scan-meetings", "mail:scan-meetings hours:48"],
    },
)
def mail_scan_meetings_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for scanning meetings."""
    hours = params.get("hours", 24)
    return scan_emails_for_meetings(hours)


# ============================================================================
# mail:add-meeting - Add meeting from email to calendar
# ============================================================================

@register_workflow(
    namespace="mail",
    name="add-meeting",
    summary="Add meeting invite from email to calendar",
    description="Extracts meeting details from an email and adds to calendar.",
    parameters=(
        ParameterSpec(
            name="email_id",
            description="Email ID containing the meeting invitation",
            type=str,
            required=True,
            aliases=["id", "message_id", "email-id"]
        ),
        ParameterSpec(
            name="time",
            description="Custom meeting time (optional, overrides email)",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:add-meeting email-id:MSG_ID [time:DATETIME]",
        "returns": "str",
        "examples": [
            "mail:add-meeting email-id:199e610074e62292",
            "mail:add-meeting email-id:199e610074e62292 time:2025-10-15T14:00:00"
        ],
    },
)
def mail_add_meeting_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for adding meeting from email."""
    email_id = params.get("email_id")
    time = params.get("time")
    
    if not email_id:
        raise WorkflowValidationError("Email ID is required")
    
    return add_meeting_from_email(email_id, time)


# ============================================================================
# mail:invite - Send meeting invitation
# ============================================================================

@register_workflow(
    namespace="mail",
    name="invite",
    summary="Send meeting invite to participants",
    description="Creates and sends a meeting invitation email.",
    parameters=(
        ParameterSpec(
            name="to",
            description="Recipient email address",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="subject",
            description="Meeting subject",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="time",
            description="Meeting time (YYYY-MM-DDTHH:MM:SS)",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="duration",
            description="Meeting duration in minutes",
            type=int,
            default=60,
        ),
        ParameterSpec(
            name="platform",
            description="Meeting platform (gmeet/zoom/teams)",
            type=str,
            default="gmeet",
        ),
        ParameterSpec(
            name="message",
            description="Additional message for the invitation",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:invite to:EMAIL subject:TEXT time:DATETIME duration:MINS [platform:TEXT] [message:TEXT]",
        "returns": "str",
        "examples": [
            "mail:invite to:team@company.com subject:Team Sync time:2025-10-15T14:00:00 duration:60",
            "mail:invite to:john@test.com subject:Interview time:2025-10-16T10:00:00 duration:30 platform:zoom"
        ],
    },
)
def mail_invite_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for sending meeting invitations."""
    to = params.get("to")
    subject = params.get("subject")
    time = params.get("time")
    duration = params.get("duration", 60)
    platform = params.get("platform", "gmeet")
    message = params.get("message")
    
    if not to or not subject or not time:
        raise WorkflowValidationError("'to', 'subject', and 'time' are required")
    
    return create_and_send_meeting_invite(to, subject, time, duration, platform, message)
