"""
Deterministic helper for invoking the local Ollama model via CLI or HTTP API.

Default behavior uses the CLI to avoid persistent contexts, but setting the
environment variable `OLLAMA_USE_HTTP=1` will switch to the persistent HTTP
endpoint (`ollama serve`) for significantly lower latency.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from typing import Any, Dict, Optional

import requests

from agent.config.runtime import LLMProfile

_OLLAMA_SUPPORTS_OPTIONS: Optional[bool] = None
_OLLAMA_OPTIONS_WARNING_EMITTED = False
_WARMED_MODELS: set[str] = set()
_OLLAMA_HTTP_URL = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
_OLLAMA_KEEPALIVE_URL = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api/generate").replace("/generate", "/ps")


def keep_model_alive(model: str = "qwen3:4b-instruct", keep_alive: str = "30m") -> bool:
    """
    Send a request to keep the model loaded in memory.
    This prevents model unloading and speeds up subsequent requests.
    
    Args:
        model: Model name to keep alive
        keep_alive: Duration to keep model loaded (e.g., "30m", "1h", "-1" for forever)
    """
    try:
        payload = {
            "model": model,
            "prompt": "",
            "keep_alive": keep_alive,
        }
        response = requests.post(
            _OLLAMA_HTTP_URL,
            json=payload,
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _detect_options_support() -> bool:
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
        _OLLAMA_SUPPORTS_OPTIONS = True
    return _OLLAMA_SUPPORTS_OPTIONS


def _build_command(model: str, options: Dict[str, Any]) -> list[str]:
    command = ["ollama", "run", model]
    if options and _detect_options_support():
        command.extend(["--options", json.dumps(options)])
    return command


def _run_via_subprocess(
    prompt: str,
    *,
    profile: LLMProfile,
    model: Optional[str],
    extra_options: Optional[Dict[str, Any]],
    timeout: Optional[int],
) -> Optional[str]:
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


def _run_via_http(
    prompt: str,
    *,
    profile: LLMProfile,
    model: Optional[str],
    extra_options: Optional[Dict[str, Any]],
    timeout: Optional[int],
) -> Optional[str]:
    resolved_model = model or profile.model
    resolved_timeout = timeout or profile.timeout_seconds

    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "stream": True,
        "options": profile.to_ollama_options(),
    }
    if extra_options:
        payload["options"].update(extra_options)

    try:
        response = requests.post(
            _OLLAMA_HTTP_URL,
            json=payload,
            timeout=resolved_timeout,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"⚠️  Ollama HTTP request failed: {exc}")
        return None

    chunks: list[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "response" in data:
            chunks.append(data["response"])
        if data.get("done"):
            break

    output = "".join(chunks).strip()
    return output or None


def run_ollama(
    prompt: str,
    *,
    profile: LLMProfile,
    model: Optional[str] = None,
    extra_options: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    stream: bool = False,
) -> Optional[str]:
    del stream
    use_http = os.getenv("OLLAMA_USE_HTTP", "0").lower() in {"1", "true", "yes", "on"}
    
    # Try HTTP first if enabled, fallback to CLI on connection error
    if use_http:
        result = _run_via_http(
            prompt,
            profile=profile,
            model=model,
            extra_options=extra_options,
            timeout=timeout,
        )
        # Fallback to CLI if HTTP fails
        if result is None:
            if os.getenv("CLAI_DEBUG") == "1":
                print("[OLLAMA] HTTP failed, falling back to CLI")
            return _run_via_subprocess(
                prompt,
                profile=profile,
                model=model,
                extra_options=extra_options,
                timeout=timeout,
            )
        return result
    else:
        return _run_via_subprocess(
            prompt,
            profile=profile,
            model=model,
            extra_options=extra_options,
            timeout=timeout,
        )


def warmup_model(profile: LLMProfile, model: Optional[str] = None) -> bool:
    resolved_model = model or profile.model
    if resolved_model in _WARMED_MODELS:
        return False

    def _ping():
        run_ollama(
            "warmup ping",
            profile=profile,
            model=resolved_model,
            timeout=profile.timeout_seconds,
        )

    threading.Thread(target=_ping, daemon=True).start()
    _WARMED_MODELS.add(resolved_model)
    return True


__all__ = ["run_ollama", "warmup_model", "keep_model_alive"]
