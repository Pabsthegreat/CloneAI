# Proposed Architecture Refactor
## Fixing the Deterministic LLM → GPT Generation Gap

> **⚠️ HISTORICAL DOCUMENT**: This architecture has been **fully implemented** as the "Tiered Architecture". See `TIERED_ARCHITECTURE_EXPLAINED.md` and `ARCHITECTURE.md` for current implementation details.

### Original Problems (Now Solved)

1. **Local LLM only generates existing commands** → Never triggers GPT generation
2. **Sequential planner is rule-based** → Doesn't consult LLM for next steps
3. **No "cannot handle" mechanism** → LLM can't request new workflow generation
4. **No chat memory** → Sequential steps lose context

### Proposed Solution: Three-Tier Intelligence System

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INSTRUCTION                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: Local LLM Classifier (Fast, Free)                  │
│  • Can I answer directly? (math, translation, etc.)          │
│  • Can I use EXISTING workflows?                             │
│  • Do I need NEW workflow? (trigger GPT)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴────────┐
                    │                │
            ┌───────▼────┐    ┌─────▼──────┐
            │  Direct     │    │  Workflow  │
            │  Answer     │    │  Execution │
            └─────────────┘    └────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼─────────┐
            │  Existing       │              │  New Workflow      │
            │  Workflow       │              │  (GPT Generation)  │
            └────────────────┘              └────────────────────┘
                    │                                   │
            ┌───────▼────────────────────────────────────▼────┐
            │  TIER 2: Sequential Execution with LLM Memory   │
            │  • Step 1 → Store result in memory               │
            │  • Ask LLM: "What next?" (with full context)     │
            │  • Step 2 → Update memory                        │
            │  • Repeat until LLM says "done"                  │
            └──────────────────────────────────────────────────┘
                                  ↓
            ┌─────────────────────────────────────────────────┐
            │  TIER 3: GPT Generation (if needed)             │
            │  • Triggered when LLM requests unknown workflow  │
            │  • Generates new workflow module                 │
            │  • Registers and executes                        │
            └──────────────────────────────────────────────────┘
```

---

## Implementation Changes

### 1. Enhanced Local LLM Response Format

**File:** `agent/tools/nl_parser.py`

```python
# NEW response structure
{
  "action_type": "direct_answer" | "existing_workflow" | "needs_new_workflow",
  
  # For direct_answer
  "answer": "The square root of 16 is 4",
  
  # For existing_workflow
  "workflow": {
    "steps": [...],
    "reasoning": "..."
  },
  
  # For needs_new_workflow
  "new_workflow_request": {
    "namespace": "math",
    "action": "fibonacci",
    "description": "Calculate fibonacci sequence",
    "example_usage": "math:fibonacci n:10"
  }
}
```

### 2. Sequential Planner with LLM + Memory

**File:** `agent/tools/sequential_planner.py`

```python
from typing import Dict, List, Any

class SequentialPlannerWithMemory:
    """
    LLM-powered sequential planner with chat memory.
    """
    
    def __init__(self):
        self.memory: List[Dict[str, str]] = []
        
    def add_to_memory(self, step_command: str, step_output: str):
        """Store step result in memory."""
        self.memory.append({
            "command": step_command,
            "output": step_output,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context_summary(self) -> str:
        """Summarize memory for LLM context."""
        if not self.memory:
            return "No previous steps."
        
        summary = "Previous steps:\n"
        for i, step in enumerate(self.memory, 1):
            summary += f"{i}. {step['command']}\n"
            summary += f"   Result: {step['output'][:100]}...\n"
        return summary
    
    def plan_next_step_with_llm(
        self, 
        original_instruction: str,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ask LLM: "Given what we've done, what's next?"
        
        Returns:
        {
          "has_next_step": true/false,
          "command": "mail:reply id:123",
          "reasoning": "User wants to reply to urgent emails",
          "is_complete": false
        }
        """
        
        context_summary = self.get_context_summary()
        
        prompt = f"""You are a sequential task planner. Decide the next step.

Original Goal: "{original_instruction}"

{context_summary}

Available context:
{json.dumps(current_context, indent=2)}

Available commands: {COMMAND_REFERENCE}

Decision: What should we do next?

Respond with JSON:
{{
  "has_next_step": true/false,
  "command": "next command to execute",
  "reasoning": "why this step is needed",
  "is_complete": true/false
}}

Rules:
- If goal is achieved, set is_complete=true
- If more steps needed, provide next command
- Use information from previous steps
- Don't repeat actions already done
"""
        
        response = call_ollama(prompt)
        # Parse and return
        ...
```

### 3. Auto Command Refactor

**File:** `agent/cli.py`

```python
@app.command()
def auto(instruction: str, run: bool = False):
    """
    Execute multi-step workflows with LLM-guided sequential planning.
    """
    
    # TIER 1: Local LLM Classification
    from agent.tools.nl_parser import classify_instruction
    
    classification = classify_instruction(instruction)
    
    if classification["action_type"] == "direct_answer":
        # No workflow needed
        typer.echo(classification["answer"])
        return
    
    if classification["action_type"] == "needs_new_workflow":
        # Trigger GPT generation
        new_workflow = classification["new_workflow_request"]
        typer.secho(f"🤖 Generating new workflow: {new_workflow['namespace']}:{new_workflow['action']}", 
                   fg=typer.colors.MAGENTA)
        
        from agent.executor.dynamic_workflow import dynamic_manager
        generation_result = dynamic_manager.ensure_workflow(
            f"{new_workflow['namespace']}:{new_workflow['action']}",
            recipe_override={
                "description": new_workflow["description"],
                "example_usage": new_workflow.get("example_usage")
            }
        )
        
        if not generation_result.success:
            typer.secho("❌ Could not generate workflow", fg=typer.colors.RED)
            return
    
    # TIER 2: Sequential Execution with Memory
    steps = classification["workflow"]["steps"]
    planner = SequentialPlannerWithMemory()
    
    typer.secho(f"\n📋 Starting workflow: {len(steps)} initial step(s)", fg=typer.colors.CYAN)
    
    step_index = 0
    while step_index < len(steps):
        step = steps[step_index]
        command = step["command"]
        
        typer.secho(f"\n▶ Step {step_index + 1}: {step['description']}", fg=typer.colors.YELLOW)
        
        # Execute step
        result = execute_single_command(command)
        typer.echo(result)
        
        # Add to memory
        planner.add_to_memory(command, result)
        
        # Ask LLM: "What's next?"
        next_step_plan = planner.plan_next_step_with_llm(
            instruction, 
            current_context={
                "available_ids": auto_context.get("mail:last_message_ids", []),
                "last_output": result
            }
        )
        
        if next_step_plan["is_complete"]:
            typer.secho("\n✅ Workflow complete!", fg=typer.colors.GREEN)
            break
        
        if next_step_plan["has_next_step"]:
            # Add dynamically planned step
            steps.append({
                "command": next_step_plan["command"],
                "description": next_step_plan["reasoning"],
                "needs_approval": False
            })
        
        step_index += 1
    
    # Log workflow with full memory
    log_command(
        command=f"auto {instruction}",
        output=planner.get_context_summary(),
        command_type="auto",
        metadata={
            "memory": planner.memory,
            "total_steps": len(planner.memory)
        }
    )
```

---

## Key Benefits

1. **✅ Local LLM can trigger GPT** - New `needs_new_workflow` action type
2. **✅ Sequential steps have context** - Memory stores all previous steps
3. **✅ LLM guides each step** - Asks "what next?" with full context
4. **✅ Dynamic workflow generation** - GPT called when needed
5. **✅ Fewer tokens** - Only GPT calls when absolutely needed

---

## Migration Path

1. **Phase 1**: Add `classify_instruction()` to `nl_parser.py` with new response format
2. **Phase 2**: Create `SequentialPlannerWithMemory` class
3. **Phase 3**: Refactor `auto()` command to use new architecture
4. **Phase 4**: Update `execute_single_command()` to handle GPT trigger from classification
5. **Phase 5**: Test and tune prompts

---

## Example Flow

```bash
$ clai auto "check my emails and reply to any urgent ones"

🧠 Local LLM: Classifying request...
✓ Action type: existing_workflow
✓ Initial plan: 2 steps

📋 Starting workflow: 2 initial steps

▶ Step 1: List recent emails
   Executing: mail:list last 10
   [Output shown]

🤔 Planning next step with LLM...
   Memory: 1 step completed
   Context: 10 message IDs available
   
▶ Step 2: View first email to check urgency
   Executing: mail:view id:MSG_001
   [Email content shown]
   
🤔 Planning next step with LLM...
   Memory: 2 steps completed
   LLM Decision: "This email is urgent, reply to it"

▶ Step 3: Reply to urgent email (added dynamically)
   Executing: mail:reply id:MSG_001
   [Reply drafted]

🤔 Planning next step with LLM...
   Memory: 3 steps completed
   LLM Decision: "Goal achieved - urgent email handled"

✅ Workflow complete!
```

---

## Implementation Status

> **✅ ALL PRIORITIES COMPLETED**

### Implemented Features:

1. ✅ **HIGH**: Fix LLM → GPT generation gap
   - **Implemented as**: `NEEDS_NEW_WORKFLOW` action type in tiered architecture
   - **File**: `agent/tools/tiered_planner.py`
   - **Enhancement**: Local LLM generates detailed context for GPT-4

2. ✅ **HIGH**: Add memory to sequential planner
   - **Implemented as**: `WorkflowMemory` dataclass with indexed context
   - **File**: `agent/tools/tiered_planner.py`
   - **Features**: Tracks original request, plan, completed steps, context

3. ✅ **MEDIUM**: Refactor `auto()` command
   - **File**: `agent/cli.py`
   - **Flow**: Guardrails (Step 0) → Classification (Step 1) → Execution (Step 2+)

### Additional Enhancements Beyond Original Proposal:

4. ✅ **Safety Guardrails**: Content moderation with qwen3:4b-instruct
   - **File**: `agent/tools/guardrails.py`

5. ✅ **LLM-Generated GPT Prompts**: Two-LLM architecture for better code quality
   - **File**: `agent/executor/gpt_workflow.py`

6. ✅ **Dynamic Category Mapping**: No hardcoded mappings
   - **File**: `agent/executor/gpt_workflow.py`

7. ✅ **Workflow Reload**: New workflows immediately available
   - **File**: `agent/cli.py` (importlib.reload)

### Documentation:
- **Current Architecture**: See `TIERED_ARCHITECTURE_EXPLAINED.md`
- **Implementation Details**: See `ARCHITECTURE.md`
- **Testing**: Successfully generated workflows for web scraping, file operations, etc.
4. **LOW**: Optimize prompts for token efficiency
