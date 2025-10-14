"""
Sequential workflow planner that generates next steps based on previous outputs.
"""

import json
import subprocess
from typing import Dict, List, Optional, Any


def plan_next_step(
    original_instruction: str,
    completed_steps: List[Dict[str, str]],
    remaining_goal: str,
    model: str = "qwen3:4b-instruct"
) -> Optional[Dict[str, Any]]:
    """
    Given what's been done, decide the next step.
    
    Args:
        original_instruction: The original user request
        completed_steps: List of {command, output} dicts for steps already done
        remaining_goal: What still needs to be accomplished
        model: Ollama model to use
        
    Returns:
        Dictionary with:
        - has_next_step: bool, whether there's more to do
        - command: str, next command to execute (if has_next_step=True)
        - description: str, what this step does
        - needs_approval: bool, whether to ask user
        - reasoning: str, why this step is needed
        
        Or None if planning fails
    """
    
    # Build context from completed steps
    context_lines = []
    for i, step in enumerate(completed_steps, 1):
        context_lines.append(f"Step {i}: {step['command']}")
        # For mail:list, extract only Message IDs
        if 'mail:list' in step['command']:
            import re
            ids = re.findall(r'Message ID: ([a-f0-9]+)', step['output'])
            context_lines.append(f"IDs: {', '.join(ids)}")
        else:
            # For other commands, keep brief
            context_lines.append(f"Output: {step['output'][:100]}")
        context_lines.append("")
    
    context = "\n".join(context_lines) if context_lines else "No steps completed yet."
    
    # Extract already-used IDs to avoid repeating them
    used_ids = []
    for step in completed_steps:
        # Extract mail IDs from commands like "mail:reply id:199e2c327ade5d86"
        import re
        id_match = re.search(r'id:([a-f0-9]+)', step['command'])
        if id_match:
            used_ids.append(id_match.group(1))
    
    used_ids_str = f"\nIMPORTANT: Already processed these IDs (DO NOT reuse): {', '.join(used_ids)}" if used_ids else ""
    
    prompt = f"""Next step?

Request: "{original_instruction}"
Done: {len(completed_steps)} steps
{context}{used_ids_str}

Rules:
- Copy EXACT ID from Step 1 output
- Use NEXT unused ID
- Process ALL items

JSON:
{{"has_next_step": true/false, "command": "mail:reply id:EXACT_ID_FROM_STEP1", "needs_approval": true}}"""

    try:
        # Use Ollama CLI - significantly faster than HTTP API
        result = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout.strip()
        
        # Debug
        if not output:
            print(f"[DEBUG] Empty output from LLM, stderr: {result.stderr[:200]}")
            return None
        
        # Extract JSON
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = output[json_start:json_end]
            parsed = json.loads(json_str)
            
            # Validate required fields
            if 'has_next_step' in parsed:
                if not parsed['has_next_step']:
                    return {"has_next_step": False}
                
                if 'command' in parsed:
                    return {
                        "has_next_step": True,
                        "command": parsed.get('command', ''),
                        "description": parsed.get('description', ''),
                        "needs_approval": parsed.get('needs_approval', False),
                        "reasoning": parsed.get('reasoning', '')
                    }
        
        return None
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


__all__ = ['plan_next_step']
