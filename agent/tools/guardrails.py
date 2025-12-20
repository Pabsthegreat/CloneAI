"""
Guardrails for filtering inappropriate or banned queries before processing.

Uses a lightweight LLM (gemma2:2b) for fast content moderation.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Optional, List

from agent.config.runtime import LOCAL_COMMAND_CLASSIFIER
from agent.core.llm.ollama import run_ollama


@dataclass
class GuardrailResult:
    """Result from guardrail check."""
    
    is_allowed: bool
    reason: str = ""
    category: str = ""  # What category of violation (if any)


# Categories we want to block
BANNED_CATEGORIES = [
    "harmful content",
    "illegal activities", 
    "violence",
    "hate speech",
    "adult content",
    "dangerous instructions",
    "spam",
    "phishing",
]


def check_query_safety(user_query: str, model: str = "qwen3:4b-instruct") -> GuardrailResult:
    """
    Check if a query is safe to process using an LLM.
    
    Args:
        user_query: The user's request
        model: Model for classification (default: qwen3:4b-instruct)
        
    Returns:
        GuardrailResult indicating if query should be allowed
    """
    prompt = f"""You are a security guardrail. Determine if a query is SAFE or UNSAFE.

QUERY: "{user_query}"

UNSAFE means asking for:
- Hacking, unauthorized access, breaking into systems
- Creating malware, viruses, exploits
- Violence, weapons, harm to people
- Illegal activities (drugs, fraud, theft)
- Hate speech, discrimination
- Adult/explicit content

SAFE means:
- Normal productivity tasks
- Information lookup
- Programming, coding help
- Security best practices (defensive)
- Learning legitimate skills

Respond with ONLY this JSON (no markdown, no explanations):
{{
  "is_safe": true,
  "category": "",
  "reason": "Normal productivity request"
}}

OR if unsafe:
{{
  "is_safe": false,
  "category": "hacking",
  "reason": "Requesting unauthorized access methods"
}}

CRITICAL: 
- "hack" = UNSAFE (unauthorized access)
- "secure" = SAFE (defensive security)
- "break into" = UNSAFE
- "protect from" = SAFE

JSON only:"""

    response = run_ollama(
        prompt,
        profile=LOCAL_COMMAND_CLASSIFIER,
        model=model,
        timeout=10,
    )

    if not response:
        return GuardrailResult(
            is_allowed=True,
            reason="Guardrail check failed, allowing query",
        )

    response = response.strip()

    # Remove markdown code blocks if present
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
        if response.startswith("json"):
            response = response[4:].strip()

    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        response = response[start:end]

    try:
        result = json.loads(response)
    except json.JSONDecodeError as exc:
        return GuardrailResult(
            is_allowed=True,
            reason=f"Guardrail JSON parse error: {exc}",
        )

    is_safe = result.get("is_safe", True)
    category = result.get("category", "")
    reason = result.get("reason", "")

    return GuardrailResult(
        is_allowed=is_safe,
        reason=reason,
        category=category,
    )


def is_model_available(model: str = "qwen3:4b-instruct") -> bool:
    """Check if the guardrail model is available in Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return model in result.stdout
    except Exception:
        return False


__all__ = [
    "check_query_safety",
    "is_model_available",
    "GuardrailResult",
    "BANNED_CATEGORIES",
]
