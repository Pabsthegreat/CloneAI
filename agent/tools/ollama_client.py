"""
Deterministic helper for invoking the local Ollama CLI with consistent options.

All modules that need to call the local LLM should use this helper to ensure we
set the same sampling parameters (temperature, top-p, seed, etc.) every time.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, Optional

from agent.config.runtime import LLMProfile

_OLLAMA_SUPPORTS_OPTIONS: Optional[bool] = None
_OLLAMA_OPTIONS_WARNING_EMITTED = False


def _detect_options_support() -> bool:
    """
    Detect whether the installed Ollama CLI supports the `--options` flag.
    We cache the result because the help command is relatively cheap but
    unnecessary to repeat on every generation.
    """
    global _OLLAMA_SUPPORTS_OPTIONS
    if _OLLAMA_SUPPORTS_OPTIONS is not None:
        return _OLLAMA_SUPPORTS_OPTIONS

    try:
        help_proc = subprocess.run(
            ["ollama", "run", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        help_text = (help_proc.stdout or "") + (help_proc.stderr or "")
        _OLLAMA_SUPPORTS_OPTIONS = "--options" in help_text
    except Exception:
        # If detection fails, assume support to avoid breaking newer versions.
        _OLLAMA_SUPPORTS_OPTIONS = True

    return _OLLAMA_SUPPORTS_OPTIONS


def _build_command(model: str, options: Dict[str, Any]) -> list[str]:
    command = ["ollama", "run", model]
    if options and _detect_options_support():
        command.extend(["--options", json.dumps(options)])
    return command


def run_ollama(
    prompt: str,
    *,
    profile: LLMProfile,
    model: Optional[str] = None,
    extra_options: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    stream: bool = False,  # kept for compatibility; CLI invocation is non-streaming
) -> Optional[str]:
    """
    Invoke the Ollama CLI using deterministic parameters from the supplied profile.

    Args:
        prompt: Prompt text to send to the model via STDIN.
        profile: LLMProfile containing defaults for model, timeout, and options.
        model: Optional override for the model name.
        extra_options: Additional Ollama options to merge on top of the profile.
        timeout: Optional override for timeout seconds.
        stream: Currently unused (CLI does not support our streaming flow).

    Returns:
        Trimmed response text, or None if invocation failed.
    """
    del stream  # streaming not supported when piping CLI output

    resolved_model = model or profile.model
    resolved_timeout = timeout or profile.timeout_seconds

    options = dict(profile.to_ollama_options())
    if extra_options:
        options.update(extra_options)
    command = _build_command(resolved_model, options)

    global _OLLAMA_OPTIONS_WARNING_EMITTED
    if options and not _detect_options_support() and not _OLLAMA_OPTIONS_WARNING_EMITTED:
        print("⚠️  Ollama CLI does not support '--options'; deterministic settings may be degraded.")
        _OLLAMA_OPTIONS_WARNING_EMITTED = True

    try:
        completed = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=resolved_timeout,
            check=False,
        )
    except FileNotFoundError:
        print("❌ Ollama CLI not found. Install from https://ollama.ai")
        return None
    except subprocess.TimeoutExpired:
        print(f"⚠️  Ollama CLI timed out after {resolved_timeout}s")
        return None
    except Exception as exc:
        print(f"⚠️  Failed to execute Ollama CLI: {exc}")
        return None

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        if stderr:
            print(f"⚠️  Ollama CLI error: {stderr}")
        return None

    stdout = completed.stdout or ""
    return stdout.strip() or None


__all__ = ["run_ollama"]
