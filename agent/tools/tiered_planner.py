"""
Tiered Architecture Planner with Memory Management

This module implements a token-efficient two-stage planning approach:
1. High-level classification (categories + planning type)
2. Step-by-step execution with selective command loading
"""

from __future__ import annotations

import datetime
import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.config.runtime import LOCAL_COMMAND_CLASSIFIER
from agent.workflows import registry as workflow_registry


@dataclass
class WorkflowMemory:
    """
    Chat memory for sequential workflow execution.
    Stores context, completed steps, and execution results.
    """
    
    original_request: str
    steps_plan: List[str]
    completed_steps: List[Dict[str, str]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    
    def add_step(self, step_instruction: str, command: str, output: str):
        """Add a completed step to memory."""
        self.completed_steps.append({
            "instruction": step_instruction,
            "command": command,
            "output": output,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def get_current_step_number(self) -> int:
        """Get the current step number (1-indexed)."""
        return len(self.completed_steps) + 1
    
    def get_remaining_steps(self) -> List[str]:
        """Get steps that haven't been executed yet."""
        completed_count = len(self.completed_steps)
        return self.steps_plan[completed_count:]
    
    def is_complete(self) -> bool:
        """Check if all planned steps are completed."""
        return len(self.completed_steps) >= len(self.steps_plan)
    
    def get_summary(self) -> str:
        """Get a concise summary of memory for LLM context."""
        summary = f"Original Request: {self.original_request}\n\n"
        summary += f"Plan ({len(self.steps_plan)} steps):\n"
        for i, step in enumerate(self.steps_plan, 1):
            status = "✓" if i <= len(self.completed_steps) else "○"
            summary += f"{status} {i}. {step}\n"
        
        if self.completed_steps:
            summary += f"\nCompleted Steps:\n"
            for step in self.completed_steps:
                summary += f"- {step['instruction']}\n"
                summary += f"  Command: {step['command']}\n"
                # Truncate output to 100 chars
                output_snippet = step['output'][:100].replace('\n', ' ')
                summary += f"  Result: {output_snippet}...\n"
        
        if self.context:
            summary += f"\nAvailable Context:\n"
            for key, value in self.context.items():
                if isinstance(value, list):
                    # For message IDs, show them indexed so LLM knows which is which
                    if "message_id" in key.lower() and value:
                        summary += f"- {key}:\n"
                        for i, item in enumerate(value[:10], 1):  # Show up to 10
                            summary += f"    Email {i}: {item}\n"
                    else:
                        summary += f"- {key}: {len(value)} items\n"
                else:
                    summary += f"- {key}: {str(value)[:50]}\n"
        
        return summary


@dataclass
class ClassificationResult:
    """Result from high-level classification (Prompt 1)."""
    
    can_handle_locally: bool
    local_answer: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    needs_sequential: bool = False
    steps_plan: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class StepExecutionPlan:
    """Result from step execution planning (Prompt 2+)."""
    
    can_execute: bool
    command: Optional[str] = None
    needs_new_workflow: bool = False
    workflow_request: Optional[Dict[str, str]] = None
    gpt_prompt: Optional[str] = None  # Natural language prompt for GPT generation
    reasoning: str = ""
    local_answer: Optional[str] = None


def _get_available_categories() -> List[str]:
    """Get list of all available command categories from registry."""
    categories = set()
    for spec in workflow_registry.list(namespace=None):
        if spec.namespace:
            categories.add(spec.namespace)
    
    # Add known categories even if no workflows registered yet
    known_categories = ["mail", "calendar", "task", "tasks", "doc", "convert", "merge", "system", "math", "text"]
    categories.update(known_categories)
    
    return sorted(list(categories))


def _get_commands_for_categories(categories: List[str]) -> str:
    """
    Get command reference for specific categories only.
    This is the key to token efficiency!
    
    Returns detailed command info with parameters so LLM understands capabilities.
    """
    if not categories:
        return ""
    
    command_ref = []
    for category in categories:
        command_ref.append(f"\n{category.upper()} COMMANDS:")
        
        # Get workflows for this category
        specs = workflow_registry.list(namespace=category)
        if specs:
            for spec in specs:
                usage = spec.metadata.get("usage", spec.command_key()) if spec.metadata else spec.command_key()
                description = spec.summary or spec.description or "No description"
                command_ref.append(f"  • {usage}")
                command_ref.append(f"    Description: {description}")
                
                # Add parameter details so LLM understands what the command can do
                if spec.parameters:
                    params_info = []
                    for param in spec.parameters:
                        param_desc = f"{param.name}"
                        if param.required:
                            param_desc += " (required)"
                        if param.description:
                            param_desc += f": {param.description}"
                        params_info.append(param_desc)
                    command_ref.append(f"    Parameters: {', '.join(params_info)}")
        else:
            command_ref.append(f"  • No commands available yet (may need generation)")
    
    return "\n".join(command_ref)


def _call_ollama(prompt: str, model: str = "qwen3:4b-instruct") -> Optional[str]:
    """Call Ollama CLI with the given prompt."""
    try:
        process = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=prompt, timeout=60)
        
        if process.returncode == 0:
            return stdout.strip()
        else:
            print(f"❌ Ollama error: {stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        process.kill()
        print("❌ Ollama request timed out (60s)")
        return None
    except FileNotFoundError:
        print("❌ Ollama not found. Please install: https://ollama.ai")
        return None
    except Exception as e:
        print(f"❌ Error calling Ollama: {str(e)}")
        return None


def _parse_json_from_response(response: str) -> Optional[Dict]:
    """Extract and parse JSON from LLM response."""
    if not response:
        return None
    
    response = response.strip()
    
    # Remove markdown code blocks if present
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
        if response.startswith("json"):
            response = response[4:].strip()
    
    # Find JSON object
    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        response = response[start:end]
    
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse JSON: {e}")
        print(f"Raw response: {response[:200]}...")
        return None


def classify_request(user_request: str) -> ClassificationResult:
    """
    PROMPT 1: High-level classification
    
    Determines:
    - Can handle locally (math, translation, etc.)
    - Which command categories are needed
    - If sequential planning is required
    - Natural language step-by-step plan
    
    This prompt uses ONLY category names, not full commands (token efficient!)
    """
    
    available_categories = _get_available_categories()
    categories_text = ", ".join(available_categories)
    
    prompt = f"""You are a task classifier for CloneAI. Analyze the request and determine the execution strategy.

USER REQUEST: "{user_request}"

AVAILABLE COMMAND CATEGORIES: {categories_text}

Today's date: {datetime.date.today()}

Your job: Classify this request into ONE of these action types:

1. LOCAL_ANSWER: ONLY for pure reasoning/math/text operations (no external data or tools)
   Examples: "what is 5+5?", "translate hello to Spanish", "define recursion", "reverse text"
   ⚠️  Use this RARELY! Most tasks need workflows.

2. WORKFLOW_EXECUTION: Any task requiring external data, APIs, files, or system interaction
   Examples: "check my emails", "schedule a meeting", "merge PDFs", "scrape website", "read file"
   ✅ When in doubt, choose WORKFLOW_EXECUTION - we can generate new workflows if needed!
   ✅ Even if no matching category exists, we can create one (system, web, file, etc.)

Respond with ONLY valid JSON (no markdown):
{{
  "action_type": "LOCAL_ANSWER" | "WORKFLOW_EXECUTION",
  
  "local_answer": "direct answer text (only if action_type=LOCAL_ANSWER)",
  
  "categories": ["mail", "calendar"],
  "needs_sequential": true,
  "steps_plan": [
    "Natural language step 1",
    "Natural language step 2"
  ],
  "reasoning": "Brief explanation of the strategy"
}}

CRITICAL STEP BREAKDOWN RULES:
❓ Ask yourself: "Can this be done in ONE command, or must I break it into MULTIPLE atomic steps?"

Examples of CORRECT step breakdown:
✓ "analyze my last 3 emails" → Break into SEPARATE steps:
  ["Retrieve last 3 emails", "Analyze email 1", "Analyze email 2", "Analyze email 3"]
  
✓ "reply to urgent emails" → Break into SEPARATE steps:
  ["List recent emails", "Check email 1 urgency", "Check email 2 urgency", "Reply to urgent one"]

✓ "check 5 emails and summarize them" → Break into SEPARATE steps:
  ["List 5 emails", "Summarize email 1", "Summarize email 2", "Summarize email 3", "Summarize email 4", "Summarize email 5"]

✗ WRONG: "analyze 3 emails" → ["Get emails", "Analyze all emails"] ❌ Too broad!
✗ WRONG: "summarize emails" → ["Summarize emails"] ❌ Not atomic!

RULE: If the request mentions a NUMBER (3 emails, 5 tasks, etc.), create that many SEPARATE steps!
RULE: Each step should be ONE atomic action that can be executed with ONE command.
RULE: Commands typically process ONE item at a time, so create one step per item.

IMPORTANT:
- For LOCAL_ANSWER: Provide the answer directly, leave categories/steps empty
- For WORKFLOW_EXECUTION: Break into ATOMIC steps (one action per step!)
- needs_sequential=true if steps depend on each other's results
- needs_sequential=false if steps can run independently
- Only list categories that are ACTUALLY needed for the task

JSON only:"""

    response = _call_ollama(prompt)
    parsed = _parse_json_from_response(response)
    
    if not parsed:
        return ClassificationResult(
            can_handle_locally=False,
            categories=[],
            needs_sequential=False,
            steps_plan=[],
            reasoning="Failed to parse classification response"
        )
    
    action_type = parsed.get("action_type", "WORKFLOW_EXECUTION")
    
    if action_type == "LOCAL_ANSWER":
        return ClassificationResult(
            can_handle_locally=True,
            local_answer=parsed.get("local_answer", ""),
            categories=[],
            needs_sequential=False,
            steps_plan=[],
            reasoning=parsed.get("reasoning", "")
        )
    
    return ClassificationResult(
        can_handle_locally=False,
        categories=parsed.get("categories", []),
        needs_sequential=parsed.get("needs_sequential", False),
        steps_plan=parsed.get("steps_plan", []),
        reasoning=parsed.get("reasoning", "")
    )


def plan_step_execution(
    current_step_instruction: str,
    memory: Optional[WorkflowMemory] = None,
    categories: Optional[List[str]] = None
) -> StepExecutionPlan:
    """
    PROMPT 2+: Plan execution of a single step
    
    Given:
    - Current step instruction (from steps_plan)
    - Memory (if sequential workflow)
    - Commands from relevant categories only
    
    Returns:
    - can_execute: Can this be done with existing commands?
    - command: The specific command to execute
    - needs_new_workflow: Should we call GPT to generate new workflow?
    - gpt_generation_prompt: Natural language prompt for GPT (if needs_new_workflow)
    """
    
    if not categories:
        categories = memory.categories if memory else []
    
    # Get commands for relevant categories only (token efficient!)
    commands_text = _get_commands_for_categories(categories)
    
    # Build memory context if available
    memory_text = ""
    if memory:
        memory_text = f"\n\nWORKFLOW MEMORY:\n{memory.get_summary()}"
    
    prompt = f"""You are a step executor for CloneAI. Execute a single workflow step.

CURRENT STEP: "{current_step_instruction}"
{memory_text}

AVAILABLE COMMANDS (from categories: {', '.join(categories)}):
{commands_text}

Today's date: {datetime.date.today()}

Your task: Determine how to execute this step.

Respond with ONLY valid JSON (no markdown):
{{
  "action_type": "LOCAL_ANSWER" | "EXECUTE_COMMAND" | "NEEDS_NEW_WORKFLOW",
  
  "local_answer": "direct answer (only if action_type=LOCAL_ANSWER)",
  
  "command": "exact command to execute (only if action_type=EXECUTE_COMMAND)",
  
  "new_workflow": {{
    "namespace": "category",
    "action": "action_name",
    "description": "what this workflow should do",
    "example_usage": "namespace:action param:value",
    "gpt_prompt": "Detailed natural language instructions for GPT about what this workflow should do, including parameter types (URL vs path, etc.), expected behavior, and context about the user's intent"
  }},
  
  "reasoning": "Why you chose this action"
}}

CRITICAL RULES:
1. LOCAL_ANSWER: Only if you can answer with pure reasoning (math, logic, text analysis)
2. EXECUTE_COMMAND: If a matching command exists in the available commands
3. NEEDS_NEW_WORKFLOW: If no existing command can do this task

For EXECUTE_COMMAND:
- Use EXACT syntax from available commands above
- Use REAL message IDs from "Available Context" (e.g., mail:last_message_ids)
- ONE command per step - do NOT try to batch multiple commands
- If you need to process multiple items, use ONE ID at a time
- NEVER use placeholder IDs like "id:1" or "id:2" - use actual IDs like "id:199e85d5b5b09017"
- NEVER use invalid syntax like [words:100] - check command reference for correct syntax

EXAMPLES OF CORRECT COMMANDS (when context has mail:last_message_ids: ["MSG123", "MSG456"]):
✓ CORRECT: mail:summarize id:MSG123
✗ WRONG: mail:summarize id:1
✗ WRONG: mail:summarize id:MSG123 id:MSG456 (can only do one at a time)
✗ WRONG: mail:summarize id:MSG123 [words:100] (invalid syntax)

For NEEDS_NEW_WORKFLOW:
❓ CRITICAL DECISION: Can an existing command ACTUALLY complete this specific task?

Check the command's Description AND Parameters to understand what it REALLY does:
- If command says "scan directory" but you need to "read file contents" → NEEDS_NEW_WORKFLOW
- If command says "list emails" but you need to "analyze sentiment" → NEEDS_NEW_WORKFLOW  
- If command says "navigate files" but you need to "scrape web page" → NEEDS_NEW_WORKFLOW
- If command accepts "path" but you need to process "URL" → NEEDS_NEW_WORKFLOW

Examples when to request new workflow:
✓ Task: "count lines in Python files"
  Available: system:scan_directory (only lists files, doesn't read contents)
  → NEEDS_NEW_WORKFLOW: system:count_lines_in_files
  
✓ Task: "fetch HTML from URL"
  Available: system:read_file (only reads local files, not web URLs)
  → NEEDS_NEW_WORKFLOW: system:fetch_html_from_url

✗ Task: "list files in directory"
  Available: system:scan_directory (lists files and directories)
  → EXECUTE_COMMAND: system:scan_directory

When requesting new workflow:
- Suggest appropriate namespace from categories: {', '.join(categories)}
- IMPORTANT: Include "gpt_prompt" - a detailed natural language description for GPT
  - Explain the user's intent clearly
  - Specify what inputs/parameters the workflow needs
  - Mention expected output format
  - Include any important context (e.g., "This is for web scraping, not file navigation")
  - Example: "Create a workflow to fetch and parse HTML from a web URL. It should accept a 'url' parameter (not a file path), make an HTTP request to that URL, parse the HTML content, and extract specific elements like title, headings, or links. This is for web scraping tasks."

JSON only:"""

    response = _call_ollama(prompt)
    parsed = _parse_json_from_response(response)
    
    if not parsed:
        return StepExecutionPlan(
            can_execute=False,
            reasoning="Failed to parse step execution response"
        )
    
    action_type = parsed.get("action_type", "EXECUTE_COMMAND")
    
    if action_type == "LOCAL_ANSWER":
        return StepExecutionPlan(
            can_execute=True,
            local_answer=parsed.get("local_answer", ""),
            reasoning=parsed.get("reasoning", "")
        )
    
    if action_type == "NEEDS_NEW_WORKFLOW":
        new_workflow = parsed.get("new_workflow", {})
        return StepExecutionPlan(
            can_execute=False,
            needs_new_workflow=True,
            workflow_request=new_workflow,
            gpt_prompt=new_workflow.get("gpt_prompt", ""),
            reasoning=parsed.get("reasoning", "")
        )
    
    # EXECUTE_COMMAND
    return StepExecutionPlan(
        can_execute=True,
        command=parsed.get("command", ""),
        reasoning=parsed.get("reasoning", "")
    )


__all__ = [
    "WorkflowMemory",
    "ClassificationResult", 
    "StepExecutionPlan",
    "classify_request",
    "plan_step_execution"
]
