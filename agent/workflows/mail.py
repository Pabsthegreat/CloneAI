"""Mail-related workflows registered with the workflow registry."""

from __future__ import annotations

import re
import shlex
from typing import Any, Dict

from agent.tools.mail import (
    get_email_messages,
    format_email_list,
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
    summary="List recent emails.",
    description="Fetches recent emails from Gmail, optionally filtered by sender.",
    parameters=(
        ParameterSpec(
            name="count",
            description="Number of emails to retrieve.",
            type=int,
            default=5,
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
    ),
    parameter_parser=_parse_mail_list,
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:list [last N] [sender:EMAIL] [query:QUERY]",
        "returns": "str",
        "examples": [
            'mail:list last 5',
            'mail:list sender:boss@example.com',
        ],
    },
)
def run_mail_list_workflow(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing emails."""
    count = params.get("count", 5)
    sender = params.get("sender")
    query = params.get("query")

    messages = get_email_messages(count=count, sender=sender, query=query)
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
