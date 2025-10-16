"""
Intelligent command classifier using the configured local LLM to determine if a
request can be answered instantly without invoking workflows or the GPT agent.
"""

from __future__ import annotations

import json
from typing import Optional

from agent.config.runtime import (
    CLASSIFIER_CAPABILITIES,
    CLASSIFIER_ESCALATE_TOPICS,
    LOCAL_COMMAND_CLASSIFIER,
    topic_list,
)
from agent.tools.ollama_client import run_ollama


def _build_classifier_prompt(instruction: str) -> str:
    capability_lines = []
    for title, examples in CLASSIFIER_CAPABILITIES:
        examples_text = ", ".join(examples)
        capability_lines.append(f"- {title}: {examples_text}")

    escalate_topics = topic_list(CLASSIFIER_ESCALATE_TOPICS)

    return (
        "Decide if you can answer the request directly without tools.\n\n"
        f"Request: \"{instruction.strip()}\"\n\n"
        "Reply with JSON only: {\"can_handle\": true/false, \"answer\": \"text or null\"}.\n"
        "Answer true only if BOTH are satisfied:\n"
        "  • You can solve it with reasoning, maths, language translation, or basic text editing.\n"
        f"  • Any required text/content is provided inline.\n\n"
        "Supported examples:\n"
        + "\n".join(capability_lines)
        + "\n\n"
        "Return false if the task touches any of these topics or requires external data/access:\n"
        f"{escalate_topics}."
    )


def can_local_llm_handle(instruction: str) -> tuple[bool, Optional[str]]:
    prompt = _build_classifier_prompt(instruction)
    response = run_ollama(prompt, profile=LOCAL_COMMAND_CLASSIFIER)
    if not response:
        return False, None

    output = response.strip()
    json_start = output.find("{")
    json_end = output.rfind("}") + 1
    if json_start == -1 or json_end <= json_start:
        return False, None

    try:
        parsed = json.loads(output[json_start:json_end])
    except json.JSONDecodeError:
        return False, None

    if parsed.get("can_handle") and parsed.get("answer"):
        return True, str(parsed["answer"])

    return False, None


__all__ = ["can_local_llm_handle"]
