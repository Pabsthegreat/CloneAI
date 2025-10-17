"""
Centralised runtime configuration for CloneAI agents.

Provides defaults for local/remote LLM selection, legacy command handling,
and heuristics used across the application. Values can be overridden via
environment variables to avoid hard-coded strings in code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


def _get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_env_chain(*names: str, default: str) -> str:
    """
    Return the first environment variable value that is set from the provided names.
    Falls back to the supplied default if none are defined.
    """
    for name in names:
        if not name:
            continue
        value = os.getenv(name)
        if value is not None:
            return value
    return default


@dataclass(frozen=True)
class LLMProfile:
    """Configuration for invoking a language model."""

    model: str
    timeout_seconds: int
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 1
    seed: int = 42
    repeat_penalty: float = 1.0

    def to_ollama_options(self) -> Dict[str, float]:
        """Return deterministic Ollama generation settings."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "seed": self.seed,
        }


LOCAL_COMMAND_CLASSIFIER = LLMProfile(
    model=_get_env("CLAI_CLASSIFIER_MODEL", "qwen3:4b-instruct"),
    timeout_seconds=int(_get_env("CLAI_CLASSIFIER_TIMEOUT", "8")),
    temperature=float(
        _get_env_chain(
            "CLAI_CLASSIFIER_TEMPERATURE",
            "CLAI_LOCAL_TEMPERATURE",
            default="0.0",
        )
    ),
    top_p=float(
        _get_env_chain(
            "CLAI_CLASSIFIER_TOP_P",
            "CLAI_LOCAL_TOP_P",
            default="1.0",
        )
    ),
    top_k=int(
        _get_env_chain(
            "CLAI_CLASSIFIER_TOP_K",
            "CLAI_LOCAL_TOP_K",
            default="1",
        )
    ),
    seed=int(
        _get_env_chain(
            "CLAI_CLASSIFIER_SEED",
            "CLAI_LOCAL_SEED",
            default="42",
        )
    ),
    repeat_penalty=float(
        _get_env_chain(
            "CLAI_CLASSIFIER_REPEAT_PENALTY",
            "CLAI_LOCAL_REPEAT_PENALTY",
            default="1.0",
        )
    ),
)

LOCAL_PLANNER = LLMProfile(
    model=_get_env("CLAI_PLANNER_MODEL", "qwen3:4b-instruct"),
    timeout_seconds=int(_get_env("CLAI_PLANNER_TIMEOUT", "60")),
    temperature=float(
        _get_env_chain(
            "CLAI_PLANNER_TEMPERATURE",
            "CLAI_LOCAL_TEMPERATURE",
            default="0.0",
        )
    ),
    top_p=float(
        _get_env_chain(
            "CLAI_PLANNER_TOP_P",
            "CLAI_LOCAL_TOP_P",
            default="1.0",
        )
    ),
    top_k=int(
        _get_env_chain(
            "CLAI_PLANNER_TOP_K",
            "CLAI_LOCAL_TOP_K",
            default="1",
        )
    ),
    seed=int(
        _get_env_chain(
            "CLAI_PLANNER_SEED",
            "CLAI_LOCAL_SEED",
            default="42",
        )
    ),
    repeat_penalty=float(
        _get_env_chain(
            "CLAI_PLANNER_REPEAT_PENALTY",
            "CLAI_LOCAL_REPEAT_PENALTY",
            default="1.0",
        )
    ),
)

REMOTE_GENERATOR_MODEL = _get_env("CLAI_GPT_MODEL", "gpt-4.1")
REMOTE_GENERATOR_TEMPERATURE = float(_get_env("CLAI_GPT_TEMPERATURE", "0.0"))
REMOTE_GENERATOR_MAX_TOKENS = int(_get_env("CLAI_GPT_MAX_TOKENS", "3000"))
REMOTE_GENERATOR_MAX_ATTEMPTS = int(_get_env("CLAI_GPT_MAX_ATTEMPTS", "1"))

LEGACY_COMMAND_PREFIXES: Tuple[str, ...] = tuple(
    prefix.strip()
    for prefix in _get_env(
        "CLAI_LEGACY_COMMAND_PREFIXES",
        ",".join(
            [
                "mail:draft",
                "mail:drafts",
                "mail:reply",
                "mail:send",
                "mail:search",
                "mail:priority",
                "doc:",
                "cal:",
                "sys:",
            ]
        ),
    ).split(",")
    if prefix.strip()
)

SEND_CONFIRMATION_KEYWORDS: Tuple[str, ...] = tuple(
    word.strip() for word in _get_env(
        "CLAI_SEND_CONFIRMATION_KEYWORDS",
        "send,deliver,dispatch,email it,mail it,forward",
    ).split(",")
    if word.strip()
)

URGENT_KEYWORDS: Tuple[str, ...] = tuple(
    word.strip() for word in _get_env(
        "CLAI_URGENT_EMAIL_KEYWORDS",
        "urgent,asap,immediately,deadline,today,tomorrow,priority,important,critical",
    ).split(",")
    if word.strip()
)

REPLY_KEYWORDS: Tuple[str, ...] = tuple(
    word.strip()
    for word in _get_env(
        "CLAI_REPLY_INTENT_KEYWORDS",
        "reply,respond,answer,write back,get back,email back",
    ).split(",")
    if word.strip()
)


CLASSIFIER_CAPABILITIES: Tuple[Tuple[str, Sequence[str]], ...] = (
    (
        "Math / calculation",
        ("5+3", "square root of 16", "what is 7 * 12"),
    ),
    (
        "General knowledge / explanations",
        ("capital of France", "what is Python", "explain gravity"),
    ),
    (
        "Text rewriting / analysis",
        ("reverse hello", "summarize this text", "analyze sentiment of ..."),
    ),
    (
        "Translation",
        ("translate hello to Spanish", "translate bonjour"),
    ),
)

CLASSIFIER_ESCALATE_TOPICS: Tuple[str, ...] = tuple(
    topic.strip()
    for topic in _get_env(
        "CLAI_CLASSIFIER_ESCALATE_TOPICS",
        "email,calendar,meeting,schedule,file,attachment,api,web,fetch,download,upload,gmail,pesuplacements",
    ).split(",")
    if topic.strip()
)


def topic_list(topics: Iterable[str]) -> str:
    return ", ".join(sorted(set(topics)))


__all__ = [
    "LLMProfile",
    "LOCAL_COMMAND_CLASSIFIER",
    "LOCAL_PLANNER",
    "REMOTE_GENERATOR_MODEL",
    "REMOTE_GENERATOR_TEMPERATURE",
    "REMOTE_GENERATOR_MAX_TOKENS",
    "REMOTE_GENERATOR_MAX_ATTEMPTS",
    "LEGACY_COMMAND_PREFIXES",
    "SEND_CONFIRMATION_KEYWORDS",
    "URGENT_KEYWORDS",
    "CLASSIFIER_CAPABILITIES",
    "CLASSIFIER_ESCALATE_TOPICS",
    "topic_list",
    "REPLY_KEYWORDS",
]
