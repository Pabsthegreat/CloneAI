"""General utility workflows registered with the workflow registry."""

from __future__ import annotations

from typing import Any, Dict

from agent.workflows import ParameterSpec, WorkflowContext, WorkflowValidationError, register_workflow


@register_workflow(
    namespace="system",
    name="hi",
    summary="Interactive greeting",
    description="Displays an interactive greeting message.",
    parameters=(),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "hi",
        "returns": "str",
        "examples": ["hi"],
    },
)
def system_hi_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for greeting."""
    return """
👋 Hello! I'm CloneAI, your intelligent command-line assistant.

Available commands:
  • mail:list [last N] - List recent emails
  • calendar:list [next N] - Show upcoming events
  • tasks - View scheduled tasks
  • Type 'clai --help' for full command reference

What can I help you with today?
"""


@register_workflow(
    namespace="system",
    name="chat",
    summary="Chat with CloneAI",
    description="Have a conversation with CloneAI assistant.",
    parameters=(
        ParameterSpec(
            name="message",
            description="Your message to CloneAI",
            type=str,
            required=True,
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "chat \"message\"",
        "returns": "str",
        "examples": [
            "chat \"How do I list my emails?\"",
            "chat \"What can you do?\""
        ],
    },
)
def system_chat_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for chat."""
    message = params.get("message")
    
    if not message:
        raise WorkflowValidationError("'message' is required")
    
    # Use local LLM to respond
    from agent.tools.nl_parser import call_ollama
    
    prompt = f"""You are CloneAI, a helpful command-line assistant. The user said: "{message}"

Respond helpfully and concisely. If they're asking about capabilities, mention:
- Email management (list, view, reply, draft)
- Calendar events
- Scheduled tasks
- Document processing

Keep responses under 100 words."""
    
    response = call_ollama(prompt, model="qwen3:4b-instruct")
    
    return response if response else "I'm here to help! Try 'clai --help' to see what I can do."


@register_workflow(
    namespace="system",
    name="history",
    summary="Show command history",
    description="Shows recent command history with optional search.",
    parameters=(
        ParameterSpec(
            name="search",
            description="Search query to filter history",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="limit",
            description="Number of history entries to show",
            type=int,
            default=20,
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "history [--search QUERY] [--limit N]",
        "returns": "str",
        "examples": [
            "history",
            "history --search mail",
            "history --limit 10"
        ],
    },
)
def system_history_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for command history."""
    from agent.state.logger import get_command_history
    
    search = params.get("search")
    limit = params.get("limit", 20)
    
    history = get_command_history(limit=limit, search=search)
    
    if not history:
        return "📝 No command history found."
    
    output = ["📝 Command History:", "=" * 80, ""]
    
    for i, entry in enumerate(history, 1):
        timestamp = entry.get("timestamp", "Unknown")
        command = entry.get("command", "Unknown")
        command_type = entry.get("command_type", "")
        
        output.append(f"{i}. [{timestamp}] {command}")
        if command_type:
            output.append(f"   Type: {command_type}")
        output.append("")
    
    return "\n".join(output)


@register_workflow(
    namespace="system",
    name="reauth",
    summary="Reauthenticate integrations",
    description="Reauthenticates with external services (Gmail, Calendar, etc.).",
    parameters=(
        ParameterSpec(
            name="service",
            description="Service to reauthenticate (gmail, calendar, all)",
            type=str,
            default="all",
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "reauth [service]",
        "returns": "str",
        "examples": [
            "reauth",
            "reauth gmail",
            "reauth calendar"
        ],
    },
)
def system_reauth_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for reauthentication."""
    service = params.get("service", "all").lower()
    
    import os
    from pathlib import Path
    
    home = Path.home()
    token_files = {
        "gmail": home / ".clai" / "token.pickle",
        "calendar": home / ".clai" / "calendar_token.pickle",
    }
    
    if service == "all":
        # Remove all tokens
        removed = []
        for svc, token_path in token_files.items():
            if token_path.exists():
                os.remove(token_path)
                removed.append(svc)
        
        if removed:
            return f"✅ Cleared authentication tokens for: {', '.join(removed)}\n\nRun any command to trigger re-authentication."
        else:
            return "ℹ️  No authentication tokens found."
    
    elif service in token_files:
        token_path = token_files[service]
        if token_path.exists():
            os.remove(token_path)
            return f"✅ Cleared {service} authentication token.\n\nRun any {service} command to trigger re-authentication."
        else:
            return f"ℹ️  No {service} authentication token found."
    
    else:
        raise WorkflowValidationError(f"Unknown service: {service}. Use 'gmail', 'calendar', or 'all'")
