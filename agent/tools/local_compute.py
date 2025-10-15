"""
Intelligent command classifier using the configured local LLM to determine if a
request can be answered instantly without invoking workflows or the GPT agent.
"""

from __future__ import annotations

import json
import subprocess
from typing import Optional, Tuple

from agent.config.runtime import (
    CLASSIFIER_CAPABILITIES,
    CLASSIFIER_ESCALATE_TOPICS,
    LOCAL_COMMAND_CLASSIFIER,
    topic_list,
)


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


def _invoke_local_model(prompt: str) -> Tuple[int, str, str]:
    """Call the configured local model via Ollama CLI."""
    result = subprocess.run(
        ["ollama", "run", LOCAL_COMMAND_CLASSIFIER.model, prompt],
        capture_output=True,
        text=True,
        timeout=LOCAL_COMMAND_CLASSIFIER.timeout_seconds,
    )
    return result.returncode, result.stdout, result.stderr


def can_local_llm_handle(instruction: str) -> tuple[bool, Optional[str]]:
    prompt = _build_classifier_prompt(instruction)
    try:
        return_code, stdout, _stderr = _invoke_local_model(prompt)
    except (subprocess.TimeoutExpired, Exception):
        return False, None

    if return_code != 0:
        return False, None

    output = stdout.strip()
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
