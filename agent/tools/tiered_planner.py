"""
Tiered Architecture Planner with Memory Management

This module implements a token-efficient two-stage planning approach:
1. High-level classification (categories + planning type)
2. Step-by-step execution with selective command loading
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.config.runtime import LLMProfile, LOCAL_PLANNER
from agent.tools.ollama_client import run_ollama
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
    # Dynamic step expansion: if current step needs breakdown into multiple steps
    needs_expansion: bool = False
    expanded_steps: List[str] = field(default_factory=list)


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


def _call_ollama(
    prompt: str,
    model: Optional[str] = None,
    *,
    profile: Optional[LLMProfile] = None,
) -> Optional[str]:
    """Call the deterministic Ollama client with the given prompt."""
    active_profile = profile or LOCAL_PLANNER
    return run_ollama(prompt, profile=active_profile, model=model)


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

1. LOCAL_ANSWER: ONLY if ENTIRE request is pure reasoning/math/text (no external data)
   Examples: "what is 5+5?", "translate hello to Spanish", "define recursion"
   If ANY part needs external data → use WORKFLOW_EXECUTION instead

2. WORKFLOW_EXECUTION: Any task requiring external data, APIs, files, or system interaction
   Examples: "check my emails", "schedule a meeting", "merge PDFs", "scrape website", "read file"
   For MIXED requests (e.g., "search X then compute Y"): Use WORKFLOW_EXECUTION with separate steps
   - Each step will be evaluated independently to see if it needs workflows or can be computed locally

CRITICAL STEP BREAKDOWN RULE:
When request mentions N items (3 emails, 5 tasks, etc.), you MUST create N+1 steps:
- Step 1: Retrieve/list the N items
- Steps 2 to N+1: One individual action per item

Example: "reply to 5 emails" MUST become 6 steps:
1. "Retrieve last 5 emails"
2. "Reply to email 1"
3. "Reply to email 2"
4. "Reply to email 3"
5. "Reply to email 4"
6. "Reply to email 5"

WRONG: ["Retrieve emails", "Reply to all"] ❌
RIGHT: ["Retrieve emails", "Reply to email 1", "Reply to email 2", ...] ✓

IMPORTANT:
- For LOCAL_ANSWER: Provide the answer directly, leave categories/steps empty
- For WORKFLOW_EXECUTION: Break into ATOMIC steps (one action, one item per step!)
- Workflows return complete data - don't add steps to "extract" or "retrieve" specific fields
- Example: "find restaurants with phone numbers" → Just ["Search for restaurants with contact info"]
- Example: "search then do math" → ["Search for X", "Compute Y"] (2 independent steps, not sequential!)
- Don't create "present" or "format" steps at the end
- If user asks for something in detail about a topic then always query the articles, read and analyse.
- needs_sequential=true ONLY if step B needs output from step A
- needs_sequential=false if steps are independent (search + math don't depend on each other)
- Only list categories that are ACTUALLY needed

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

JSON only:"""

    response = _call_ollama(prompt)
    print(f"\n[Classification Response]: {response}\n")
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

Your task: Determine how to execute this step, and generate more steps if you cannot execute it in a single step"

CRITICAL RULES:
1. LOCAL_ANSWER: Pure reasoning, math, logic, text analysis that needs no external data/tools
2. EXECUTE_COMMAND: If a matching command exists and step is atomic (one action, one item)
3. NEEDS_EXPANSION: If step needs breakdown (e.g., "Reply to 5 emails" → 5 separate reply steps)
4. NEEDS_NEW_WORKFLOW: If no existing command can do this task

⚠️ SEARCH WORKFLOW GUIDANCE:
- For "what is", "how many", "statistics", "current data" questions → USE search:web or search:deep
- For "in detail" or in depth queries or some explanation from the results... → USE search:web and use the urls from the result search:deep to get inference
- search:web exists and works for ANY internet query (news, facts, statistics, current info)
- search:deep extracts actual content from webpages for comprehensive answers
- for "in detail" or in depth queries or some explanation from the results... → USE search:deep
- DO NOT create new search workflows - use existing ones!
- Only request new workflow if task is truly unique and not searchable

IMPORTANT: Before choosing EXECUTE_COMMAND, check if the step can be done with LOCAL_ANSWER!
Examples: Simple math, text manipulation, translations can be computed directly


Respond with ONLY valid JSON (no markdown):
{{
  "action_type": "LOCAL_ANSWER" | "EXECUTE_COMMAND" | "NEEDS_NEW_WORKFLOW" | "NEEDS_EXPANSION",
  
  "local_answer": "direct answer (only if action_type=LOCAL_ANSWER)",
  
  "command": "exact command to execute (only if action_type=EXECUTE_COMMAND)",
  
  "new_workflow": {{
    "namespace": "category",
    "action": "action_name",
    "description": "what this workflow should do",
    "example_usage": "namespace:action param:value",
    "gpt_prompt": "Detailed natural language instructions for GPT about what this workflow should do, including parameter types (URL vs path, etc.), expected behavior, and context about the user's intent"
  }},
  
  "expanded_steps": ["step 1", "step 2", "step 3"],
  
  "reasoning": "Why you chose this action"
}}

For EXECUTE_COMMAND:
- Use EXACT syntax: namespace:action param1:value param2:"quoted value"
- DO NOT use function syntax with parentheses: namespace:action(param:value)
- DO NOT use brackets for optional parameters: [param:value] is WRONG, just param:value
- Use REAL IDs from "Available Context" (e.g., id:199e85d5b5b09017, NOT id:1)
- CRITICAL QUOTING RULES:
  * ALL parameter values containing spaces, punctuation, or special characters MUST be quoted with double quotes
  * Examples of CORRECT quoting:
    - title:"Meeting with John Smith"
    - body:"Thank you for your message. I will follow up soon."
    - subject:"Importance of Physical Activity"
    - to:"user@example.com"
  * Examples of WRONG (will fail):
    - title:Meeting with John Smith
    - body:Thank you for your message
    - subject:Importance of Physical Activity
  * Single-word values and numbers can be unquoted: count:5 duration:60 id:abc123
- CORRECT full examples:
  * calendar:create title:"Team Meeting" start:"2025-10-17T16:30:00" duration:60
  * mail:reply id:199e85d5b5b09017 body:"Thank you for your message. I will respond soon."
  * mail:draft to:"me@gmail.com" subject:"Physical Activity" body:"Exercise is important for health."
  * search:web query:"latest AI news" num_results:5
  * search:deep query:"Ayodhya temple statistics" num_results:3
- ✅ COMMAND CHAINING SUPPORTED (use && to chain multiple commands):
  * When step requires same action on multiple items, CHAIN THEM with &&
  * Example: mail:download id:abc123 && mail:download id:def456 && mail:download id:xyz789
  * Example: mail:summarize id:abc123 words:50 && mail:summarize id:def456 words:50
  * Example: mail:view id:msg1 && mail:view id:msg2 && mail:view id:msg3
  * Benefits: More efficient, completes entire step in one execution
  * Each command in chain uses same syntax rules (proper quoting!)
  * Use NEEDS_EXPANSION only if logic between commands is complex or different
- Prefer chaining when doing same action on multiple items from context

For NEEDS_EXPANSION:
- Use when current step is too broad and needs breakdown into atomic actions
- Create one sub-step per item (e.g., "Reply to email 1", "Reply to email 2", etc.)
- Use context to determine exact number of items available
- Each expanded step should be executable with ONE command

For NEEDS_NEW_WORKFLOW:
- Check if existing command's description AND parameters match your specific task
- If command does something different (scan vs read, local vs URL), request new workflow
- Suggest namespace from: {', '.join(categories)}
- Include "gpt_prompt" with: user intent, required parameters, expected output, important context

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
    
    if action_type == "NEEDS_EXPANSION":
        return StepExecutionPlan(
            can_execute=False,
            needs_expansion=True,
            expanded_steps=parsed.get("expanded_steps", []),
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
