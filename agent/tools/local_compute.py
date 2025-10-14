"""
Intelligent command classifier using LLM to determine if requests can be handled
directly without creating workflows or calling GPT.
"""

from typing import Optional, Dict, Any
import subprocess
import json


def can_local_llm_handle(instruction: str) -> tuple[bool, Optional[str]]:
    """
    Use local LLM to determine if it can handle this instruction directly.
    Uses Ollama CLI which is ~4x faster than HTTP API.
    
    Returns:
        (can_handle, result_or_none)
    """
    prompt = f"""Can you answer this WITHOUT external tools?

Request: "{instruction}"

Answer YES (can_handle=true) ONLY if:
- Pure math: "5+3", "square root of 16"  
- Facts: "capital of France"
- Text ops: "reverse hello"

Answer NO (can_handle=false) if needs:
- Email (read/send/check)
- Calendar (schedule/meetings)
- Files (read/write/edit)
- APIs or external data

JSON: {{"can_handle": true/false, "answer": "direct answer or null"}}"""

    try:
        # Use Ollama CLI - significantly faster than HTTP API
        result = subprocess.run(
            ['ollama', 'run', 'qwen3:4b-instruct', prompt],
            capture_output=True,
            text=True,
            timeout=5  # Reduced timeout since CLI is faster
        )
        
        if result.returncode != 0:
            return False, None
        
        output = result.stdout.strip()
        
        # Try to parse JSON from the output
        # Sometimes LLM adds extra text, so find the JSON block
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = output[json_start:json_end]
            parsed = json.loads(json_str)
            
            if parsed.get('can_handle', False):
                answer = parsed.get('answer')
                if answer:
                    return True, answer
        
        return False, None
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        # If LLM fails, fall back to "cannot handle"
        return False, None


__all__ = ['can_local_llm_handle']
