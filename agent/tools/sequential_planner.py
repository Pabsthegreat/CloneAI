"""
Deterministic sequential workflow planner.

Provides lightweight reasoning to decide the next step when workflows include
placeholder commands (e.g., `mail:view id:MESSAGE_ID`). The planner avoids
hard-coded prompts by relying on heuristics and configuration data instead of
prompting a local LLM for every decision.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agent.config.runtime import REPLY_KEYWORDS, URGENT_KEYWORDS


def _unique_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        ordered.append(value)
        seen.add(value)
    return ordered


def _extract_ids_from_list_output(output: str) -> List[str]:
    return re.findall(r"Message ID:\s*([^\s]+)", output or "", flags=re.IGNORECASE)


def _collect_available_ids(
    completed_steps: List[Dict[str, str]],
    context: Dict[str, Any],
) -> List[str]:
    ids: List[str] = []
    ids.extend(context.get("mail:last_message_ids", []))

    if not ids:
        for step in completed_steps:
            if step["command"].startswith("mail:list"):
                ids.extend(_extract_ids_from_list_output(step.get("output", "")))

    return _unique_preserve_order(ids)


def _extract_viewed_ids(completed_steps: List[Dict[str, str]]) -> List[str]:
    ids: List[str] = []
    for step in completed_steps:
        if step["command"].startswith("mail:view"):
            match = re.search(r"id:([^\s]+)", step["command"], flags=re.IGNORECASE)
            if match:
                ids.append(match.group(1))
    return _unique_preserve_order(ids)


def _score_text(text: str) -> int:
    if not text:
        return 0
    lower = text.lower()
    score = 0
    for keyword in URGENT_KEYWORDS:
        if keyword in lower:
            score += 3
    if "today" in lower or "tomorrow" in lower:
        score += 2
    if re.search(r"\b\d{1,2}(:\d{2})?\b", lower):  # mentions specific time
        score += 1
    if "http" in lower or "link" in lower:
        score += 1
    return score


def _build_email_context(
    context: Dict[str, Any],
    completed_steps: List[Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    info: Dict[str, Dict[str, str]] = {}
    for message in context.get("mail:last_messages", []):
        message_id = message.get("id")
        if not message_id:
            continue
        info.setdefault(message_id, {})
        info[message_id]["subject"] = message.get("subject", "")
        info[message_id]["snippet"] = message.get("snippet", "")

    for step in completed_steps:
        if step["command"].startswith("mail:view"):
            match = re.search(r"id:([^\s]+)", step["command"], flags=re.IGNORECASE)
            if not match:
                continue
            message_id = match.group(1)
            info.setdefault(message_id, {})
            info[message_id]["body"] = step.get("output", "")

    return info


def _pick_most_urgent_email(
    email_info: Dict[str, Dict[str, str]],
    fallback_ids: List[str],
) -> Optional[str]:
    best_id: Optional[str] = None
    best_score = 0
    for message_id in fallback_ids:
        details = email_info.get(message_id, {})
        score = (
            _score_text(details.get("subject", ""))
            + _score_text(details.get("snippet", ""))
            + _score_text(details.get("body", ""))
        )
        if score > best_score:
            best_score = score
            best_id = message_id
    return best_id if best_score > 0 else (fallback_ids[0] if fallback_ids else None)


def _select_reply_target(
    instruction_lower: str,
    available_ids: List[str],
    viewed_ids: List[str],
) -> Optional[str]:
    if not available_ids:
        return None

    if "last" in instruction_lower:
        return available_ids[-1]
    if "first" in instruction_lower or "top" in instruction_lower:
        return available_ids[0]
    if viewed_ids:
        return viewed_ids[-1]
    return available_ids[0]


def plan_next_step(
    original_instruction: str,
    completed_steps: List[Dict[str, str]],
    remaining_goal: str,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Decide the next step for a workflow that contains placeholder commands.

    Args:
        original_instruction: The original user instruction.
        completed_steps: List of executed steps (command + output).
        remaining_goal: High-level goal from the workflow planner.
        context: Additional metadata captured during execution (e.g., email IDs).
    """

    context = context or {}
    instruction_lower = original_instruction.lower()

    available_ids = _collect_available_ids(completed_steps, context)
    if not available_ids:
        return None

    viewed_ids = _extract_viewed_ids(completed_steps)
    unviewed_ids = [msg_id for msg_id in available_ids if msg_id not in viewed_ids]

    if unviewed_ids:
        next_id = unviewed_ids[0]
        return {
            "has_next_step": True,
            "command": f"mail:view id:{next_id}",
            "description": "View email content before deciding next action.",
            "needs_approval": False,
            "reasoning": "Unviewed emails remain; inspect them before replying.",
        }

    email_info = _build_email_context(context, completed_steps)
    wants_urgent = any(keyword in instruction_lower for keyword in URGENT_KEYWORDS)
    wants_reply = any(keyword in instruction_lower for keyword in REPLY_KEYWORDS)

    if wants_urgent:
        urgent_id = _pick_most_urgent_email(email_info, available_ids)
        if urgent_id:
            return {
                "has_next_step": True,
                "command": f"mail:reply id:{urgent_id}",
                "description": "Reply to the most time-sensitive email.",
                "needs_approval": True,
                "reasoning": "All emails reviewed; selected the message with the strongest urgency signals.",
            }

    if wants_reply:
        target_id = _select_reply_target(instruction_lower, available_ids, viewed_ids)
        if target_id:
            return {
                "has_next_step": True,
                "command": f"mail:reply id:{target_id}",
                "description": "Reply to the selected email.",
                "needs_approval": True,
                "reasoning": "All emails reviewed; preparing a reply as requested.",
            }

    return {"has_next_step": False, "reasoning": remaining_goal}


__all__ = ["plan_next_step"]
