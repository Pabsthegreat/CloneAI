# Tiered Architecture: How It Works

## Overview

The new tiered architecture solves the fundamental problem: **A deterministic LLM that only generates existing commands will never trigger GPT generation for new workflows.**

## The Solution: Two-Stage Planning with Memory

### Architecture Flow

```
User Request: "check my last 5 emails and reply to urgent ones"
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PROMPT 1: High-Level Classification (Token-Efficient)       │
│ Input: Request + Command CATEGORIES (not full commands)     │
│ LLM receives: ~500 tokens                                   │
│                                                              │
│ Output:                                                      │
│ {                                                            │
│   "action_type": "WORKFLOW_EXECUTION",                       │
│   "categories": ["mail"],                                    │
│   "needs_sequential": true,                                  │
│   "steps_plan": [                                            │
│     "List recent emails",                                    │
│     "Identify urgent emails",                                │
│     "Reply to urgent ones"                                   │
│   ]                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Initialize Memory (if needs_sequential=true)                │
│                                                              │
│ memory = {                                                   │
│   original_request: "check my last 5...",                    │
│   steps_plan: ["List...", "Identify...", "Reply..."],       │
│   completed_steps: [],                                       │
│   context: {},                                               │
│   categories: ["mail"]                                       │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PROMPT 2: Execute Step 1 - "List recent emails"             │
│ Input: Step instruction + Memory + Mail commands only       │
│ LLM receives: ~2000 tokens (only mail commands!)            │
│                                                              │
│ Output:                                                      │
│ {                                                            │
│   "action_type": "EXECUTE_COMMAND",                          │
│   "command": "mail:list last 5"                              │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Execute command
                            ↓
                    Store in memory:
                    - command: "mail:list last 5"
                    - output: "5 emails listed..."
                    - context: {mail:last_message_ids: [...]}
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PROMPT 3: Execute Step 2 - "Identify urgent emails"         │
│ Input: Step + Memory (with previous results)                │
│                                                              │
│ LLM can see:                                                 │
│ - Original request                                           │
│ - Step 1 was completed                                       │
│ - 5 message IDs are available in context                    │
│                                                              │
│ Output:                                                      │
│ {                                                            │
│   "action_type": "NEEDS_NEW_WORKFLOW",                       │
│   "new_workflow": {                                          │
│     "namespace": "mail",                                     │
│     "action": "check-urgency",                               │
│     "description": "Analyze email urgency"                   │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Trigger GPT Generation
                            ↓
                Generate new workflow module
                            ↓
                    Re-plan step 2 with new workflow
                            ↓
                    Execute and continue...
```

---

## Key Features

### 1. **Token Efficiency** 💰

**Traditional Approach:**
```
Every prompt: [ALL 200 COMMANDS] + instruction = ~8000 tokens
3 steps = 24,000 tokens
```

**Tiered Approach:**
```
Prompt 1: [CATEGORIES ONLY] = ~500 tokens
Prompt 2: [MAIL COMMANDS ONLY] = ~2000 tokens
Prompt 3: [MAIL COMMANDS ONLY] + memory = ~3000 tokens
3 steps = 5,500 tokens (77% savings!)
```

### 2. **Chat Memory** 🧠

Each step has full context of what happened before:

```python
memory.get_summary() returns:

"""
Original Request: check my last 5 emails and reply to urgent ones

Plan (3 steps):
✓ 1. List recent emails
✓ 2. Identify urgent emails
○ 3. Reply to urgent ones

Completed Steps:
- List recent emails
  Command: mail:list last 5
  Result: Found 5 emails...
  
- Identify urgent emails  
  Command: mail:check-urgency ids:MSG1,MSG2,MSG3,MSG4,MSG5
  Result: MSG2 and MSG4 are urgent

Available Context:
- mail:last_message_ids: 5 items
- mail:urgent_message_ids: 2 items
"""
```

### 3. **GPT Generation Trigger** 🤖

LLM can explicitly request new workflows:

```python
{
  "action_type": "NEEDS_NEW_WORKFLOW",
  "new_workflow": {
    "namespace": "mail",
    "action": "check-urgency",
    "description": "Analyze email content and determine urgency level",
    "example_usage": "mail:check-urgency ids:MSG1,MSG2"
  }
}
```

This solves the problem: **Local LLM can now trigger GPT generation!**

### 4. **Step-by-Step Execution** 📝

LLM sees its own plan and decides how to execute each step:

```
Step 1: "List recent emails"
  → LLM: "Use mail:list command"
  
Step 2: "Identify urgent emails"  
  → LLM: "I need a new workflow for this" → GPT generates it
  
Step 3: "Reply to urgent ones"
  → LLM: "Use mail:reply with IDs from context"
```

---

## Implementation Details

### Memory Structure

```python
@dataclass
class WorkflowMemory:
    original_request: str
    steps_plan: List[str]
    completed_steps: List[Dict[str, str]]  # instruction, command, output
    context: Dict[str, Any]  # mail:last_message_ids, etc.
    categories: List[str]  # mail, calendar, etc.
```

### Two-Stage Classification

**Stage 1: What kind of task is this?**
- Can I answer directly? (math, translation)
- What categories of commands do I need?
- Do steps depend on each other?

**Stage 2: How do I execute each step?**
- Can I use an existing command?
- Do I need a new workflow?
- Can I compute this locally?

---

## Example Execution

### Simple Request (No Memory Needed)

```bash
$ clai auto "convert hello to uppercase"

🧠 Analyzing request...
📊 Step 1: Classifying request type...

✓ Classification complete:
  Categories: []
  Sequential: No
  Steps: 1

💡 Computed locally (no workflows needed):
HELLO

✅ Workflow completed!
```

**Total tokens: ~500** (only classification prompt)

### Complex Request (With Memory)

```bash
$ clai auto "check my last 3 emails and reply to any from john@example.com"

🧠 Analyzing request...
📊 Step 1: Classifying request type...

✓ Classification complete:
  Categories: mail
  Sequential: Yes
  Steps: 3
  
💾 Sequential workflow detected - initializing memory

🚀 Executing workflow...

▶ Step 1/3: Check last 3 emails
   Planning execution...
   Strategy: Use mail:list command with limit parameter
   Command: mail:list last 3
   
   [3 emails listed with IDs]
   
▶ Step 2/3: Filter emails from john@example.com
   Planning execution...
   Strategy: Analyze sender from previous step context
   💡 Computed locally:
   Found 1 email from john@example.com: MSG_002
   
▶ Step 3/3: Reply to filtered emails
   Planning execution...
   Strategy: Use mail:reply with ID from context
   Command: mail:reply id:MSG_002
   
   [Reply drafted]

✅ Workflow completed!
📊 Execution Summary:
   Steps completed: 3/3
   Context collected: mail:last_message_ids, mail:filtered_ids
```

**Total tokens: ~6,000** (3 prompts with focused context)

---

## Why This Works

### Problem Solved: Deterministic → GPT Gap

**Before:**
```
Local LLM → generates "mail:list" (exists)
         → execute_single_command()
         → WorkflowNotFoundError NEVER HAPPENS
```

**After:**
```
Local LLM → classifies task
         → identifies needed categories
         → for each step:
             - tries existing commands
             - OR requests new workflow → GPT generation
             - OR computes locally
```

### Memory Enables Intelligence

Without memory:
- Each step is isolated
- Can't reference previous results
- Can't make context-aware decisions

With memory:
- LLM sees full conversation history
- Can extract IDs from previous steps
- Can skip unnecessary steps
- Can adapt plan based on results

---

## Configuration

The tiered planner uses the same LLM as before (Qwen3:4b-instruct by default) but with optimized prompts:

```python
# In agent/config/runtime.py
LOCAL_COMMAND_CLASSIFIER = ModelConfig(
    model="qwen3:4b-instruct",
    timeout_seconds=30
)
```

---

## Future Enhancements

1. **Adaptive Planning**: LLM can modify the plan mid-execution
2. **Context Pruning**: Automatically remove irrelevant context to save tokens
3. **Multi-Model Support**: Use different models for classification vs execution
4. **Caching**: Cache category → commands mapping to reduce lookups

---

## Comparison with Old Architecture

| Feature | Old Architecture | New Tiered Architecture |
|---------|-----------------|-------------------------|
| Token usage per workflow | ~24,000 | ~6,000 (75% savings) |
| GPT generation trigger | Manual/Error-based | Explicit LLM request |
| Memory | None | Full chat history |
| Step planning | Hardcoded rules | LLM-guided |
| Command loading | All commands every time | Category-filtered |
| Local computation | Separate check | Integrated in flow |

---

## Testing the Architecture

```bash
# Test local answer (no workflows)
clai auto "what is 5 squared?"

# Test existing workflow
clai auto "list my last 10 emails"

# Test sequential with memory
clai auto "check my last 5 emails and tell me which ones are urgent"

# Test GPT generation
clai auto "calculate fibonacci sequence up to 10"
```

---

---

## Recent Enhancements

### 5. **Safety Guardrails** 🛡️ (NEW)

**Purpose**: Block inappropriate or malicious queries before they reach workflow execution.

**Flow**:
```
User Request → STEP 0: Guardrails Check → STEP 1: Classification → ...
                       ↓
                   Is Safe?
                   ↙     ↘
                 YES      NO
                  ↓        ↓
             Continue    Block & Exit
```

**Implementation**:
```python
@app.command()
def auto(request: str):
    # Step 0: Safety check (FIRST LINE OF DEFENSE)
    guardrail_result = check_query_safety(request)
    
    if not guardrail_result.is_safe:
        typer.secho(f"❌ Query blocked: {guardrail_result.reason}", fg=typer.colors.RED)
        return  # Don't proceed to classification
    
    # Step 1: Classification (tiered planner)
    result = classify_request(request, registry)
    # ...
```

**Model**: qwen3:4b-instruct (local)
- **Why not gemma3:1b?** Too weak, passes malicious queries
- **Timeout**: 10 seconds
- **Fail-open**: If check fails/times out, allows query (availability over security)

**Banned Categories**:
```python
["hacking", "illegal", "violence", "harassment", 
 "malware", "phishing", "spam", "fraud",
 "privacy_violation", "unauthorized_access"]
```

**Examples**:
- ❌ **BLOCKED**: "how to hack someone's email"
- ✅ **ALLOWED**: "secure my email account"

---

### 6. **LLM-Generated GPT Prompts** 🤖 (NEW)

**Purpose**: Improve GPT workflow generation quality by having the local LLM generate detailed natural language context.

**The Problem**:
- GPT-4 with minimal context generates code with hallucinations
- Missing parameters, incorrect error handling, wrong imports

**The Solution**: Two-LLM Architecture

**Local LLM (qwen3:4b-instruct)**: Context Generator
```python
# In tiered_planner.py
prompt = f"""
User wants: "{user_request}"
Existing commands: {command_list}

Generate detailed requirements for a new workflow:
- What should it do?
- What parameters does it need?
- What should it return?
- How should errors be handled?
"""

user_context = ollama_chat(prompt)
# Returns detailed description with types, edge cases, error handling
```

**Cloud LLM (GPT-4.1)**: Code Generator
```python
# In gpt_workflow.py
recipe = WorkflowRecipe(
    namespace="system",
    name="fetch_html_from_url",
    user_request="fetch HTML from https://example.com",
    user_context=user_context,  # ← LLM-generated context
    command_catalog=registry.list_workflows()
)

code = generate_workflow_code(recipe)
```

**Quality Improvements**:

Before (no LLM context):
```python
# GPT hallucinated parameters that don't exist
@click.option('--choices', type=click.Choice(['a', 'b']))
def my_workflow(choices):
    ctx.fail("error")  # ctx.fail() doesn't exist in our system
```

After (with LLM context):
```python
# Correct implementation
@register_workflow("system", "fetch_html")
def fetch_html(url: str) -> Dict:
    import requests
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {"success": True, "html": response.text}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}
```

**Flow**:
```
User Request → classify_request() → NEEDS_NEW_WORKFLOW
                                           ↓
                              Local LLM generates context
                                           ↓
                              GPT-4 generates code with context
                                           ↓
                              Save to agent/workflows/generated/
                                           ↓
                              Reload registry
                                           ↓
                              Re-classify and execute
```

---

### 7. **Dynamic Category Mapping** 🔄 (NEW)

**Purpose**: Eliminate hardcoded category mappings by deriving categories from existing workflows.

**Before** (Hardcoded):
```python
# agent/executor/gpt_workflow.py (OLD)
NAMESPACE_TO_CATEGORY = {
    "mail": "mail",
    "calendar": "calendar",
    "document": "document",
    "system": "system"
}

def get_category(namespace: str) -> str:
    return NAMESPACE_TO_CATEGORY.get(namespace, "general")
```

**After** (Dynamic):
```python
# agent/executor/gpt_workflow.py (NEW)
def _get_category_for_namespace(namespace: str, command_catalog: Dict) -> str:
    """
    Map workflow namespace to category based on existing workflows.
    Falls back to 'general' if namespace not found.
    """
    namespace_to_category = {}
    for category, workflows in command_catalog.items():
        for workflow in workflows:
            ns = workflow.split(':')[0]  # Extract namespace from "mail:list"
            namespace_to_category[ns] = category
    
    return namespace_to_category.get(namespace, 'general')
```

**Benefits**:
- ✅ No maintenance burden (no hardcoded mappings to update)
- ✅ Automatically adapts as new workflows are added
- ✅ New categories emerge organically
- ✅ Extensible without code changes

**Example**:
```python
# When a new "notion" workflow is registered:
@register_workflow("notion", "create_page")
def create_notion_page(...):
    pass

# Category mapping automatically includes:
# {"notion": "notion"}
# No code changes needed!
```

---

### 8. **Workflow Reload After Generation** 🔄 (NEW)

**Purpose**: Make newly generated workflows immediately available without restarting the CLI.

**Implementation**:
```python
# In cli.py auto() command
if result.get("action") == "NEEDS_NEW_WORKFLOW":
    # Generate workflow
    success = generate_and_save_workflow(...)
    
    if success:
        # Reload registry to include new workflow
        import importlib
        from agent.workflows import registry
        importlib.reload(registry)
        
        # Re-classify with updated registry
        result = classify_request(request, registry)
        # Now the new workflow is available!
```

**Flow**:
```
Request → No matching workflow
              ↓
       GPT generates new workflow
              ↓
       Save to agent/workflows/generated/
              ↓
       importlib.reload(registry)  ← KEY STEP
              ↓
       Re-classify request
              ↓
       New workflow found and executed!
```

**Benefits**:
- ✅ Seamless user experience (no restart needed)
- ✅ Generated workflows immediately testable
- ✅ Supports iterative workflow development

---

## Conclusion

The tiered architecture transforms CloneAI from a **rigid command executor** into an **intelligent workflow orchestrator** with:

**Core Features**:
✅ Uses 75% fewer tokens
✅ Can trigger GPT generation when needed
✅ Maintains context across steps
✅ Makes intelligent decisions
✅ Adapts to new requirements
✅ Scales to complex multi-step tasks

**Safety & Quality**:
✅ Guardrails block malicious queries
✅ LLM-generated GPT prompts improve code quality
✅ Dynamic categories eliminate maintenance burden
✅ Automatic workflow reload for seamless UX

**This is the complete, production-ready architecture you envisioned!** 🎉
