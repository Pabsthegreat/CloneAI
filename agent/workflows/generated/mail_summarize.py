"""Mail summarization workflow - fetches and summarizes email content."""

from typing import Any, Dict

from agent.config.runtime import LOCAL_PLANNER
from agent.tools.mail import get_full_email
from agent.tools.ollama_client import run_ollama
from agent.workflows import ParameterSpec, WorkflowContext, register_workflow


def _summarize_text_locally(text: str, word_count: int = 50, model: str = "qwen3:4b-instruct") -> str:
    """Use local LLM to summarize text."""
    prompt = f"""Summarize the following text in exactly {word_count} words. Be concise and capture the key points.

Text:
{text[:4000]}

Provide ONLY the {word_count}-word summary (no extra commentary):"""
    
    response = run_ollama(
        prompt,
        profile=LOCAL_PLANNER,
        model=model,
        timeout=15,
    )

    if not response:
        return "❌ Summarization failed: no response from Ollama"

    return response.strip()


@register_workflow(
    namespace="mail",
    name="summarize",
    summary="Fetch and summarize email content",
    description="Retrieves an email by ID and generates a concise summary using local LLM. Can specify word count for summary length.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Message ID of the email to summarize",
            type=str,
            required=True,
            aliases=["message_id", "msg_id"]
        ),
        ParameterSpec(
            name="words",
            description="Target word count for summary (default: 50)",
            type=int,
            default=50,
            aliases=["length", "word_count"]
        ),
    ),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:summarize id:MESSAGE_ID [words:N]",
        "returns": "str",
        "examples": [
            "mail:summarize id:abc123",
            "mail:summarize id:abc123 words:100",
            "mail:summarize id:199e3974e450ca86 words:50"
        ]
    }
)
def mail_summarize_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Handler for email summarization."""
    message_id = params.get("id")
    word_count = params.get("words", 50)
    
    if not message_id:
        return "❌ Error: message ID is required"
    
    try:
        # Fetch email content
        email_content = get_full_email(message_id)
        
        # Extract just the body text for summarization (remove headers)
        body_start = email_content.find("Body:")
        if body_start != -1:
            text_to_summarize = email_content[body_start:]
        else:
            text_to_summarize = email_content
        
        # Summarize using local LLM
        summary = _summarize_text_locally(text_to_summarize, word_count=word_count)
        
        # Format output
        result = f"""📧 Email Summary ({word_count} words)
{'='*80}

{summary}

{'='*80}
💡 Use 'mail:view id:{message_id}' to read full email
"""
        
        # Store in context
        if ctx.extras is not None:
            ctx.extras["mail:summarized_message_id"] = message_id
            ctx.extras["mail:summary"] = summary
        
        return result
        
    except Exception as e:
        return f"❌ Error summarizing email: {str(e)}"
