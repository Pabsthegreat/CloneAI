# CloneAI - Comprehensive Flow of Control

This document traces the complete execution flow when a user runs a command like `clai auto "summarize my last email"`.

---

## 📋 Table of Contents

1. [Command Entry Point](#1-command-entry-point)
2. [Workflow Parsing Flow](#2-workflow-parsing-flow)
3. [Workflow Execution Flow](#3-workflow-execution-flow)
4. [Command Execution Flow](#4-command-execution-flow)
5. [Dynamic Workflow Generation](#5-dynamic-workflow-generation)
6. [Complete Call Stack Example](#6-complete-call-stack-example)

---

## 1. Command Entry Point

### Entry: Shell Command
```bash
clai auto "summarize my last email"
```

### File: `clai.ps1` / `setup-clai.sh`
**Location:** Project root
- Shell wrapper that invokes Python CLI
- Sets up environment and paths
- Calls: `python -m agent.cli auto "summarize my last email"`

---

## 2. Workflow Parsing Flow

### 2.1 CLI Handler - `auto()` function
**File:** `agent/cli.py`
**Lines:** 1628-1878
**Function:** `auto(instruction: str, run: bool)`

```python
def auto(instruction: str, run: bool):
    # Entry point for multi-step workflow execution
```

**Flow:**
1. Prints system info and workflow title
2. Calls `parse_workflow()` to convert natural language → workflow steps
3. If parsing fails, tries `can_local_llm_handle()` as fallback
4. Displays workflow plan to user
5. Requests approval (unless `--run` flag is set)
6. Executes workflow steps sequentially

**Key Decision Points:**
- Empty steps? → Try local LLM fallback
- Single step? → Check if local LLM can handle
- Multiple steps? → Execute workflow pipeline

---

### 2.2 Natural Language Parser - `parse_workflow()`
**File:** `agent/tools/nl_parser.py`
**Lines:** 289-370
**Function:** `parse_workflow(instruction: str, model: str)`

```python
def parse_workflow(instruction: str, model: str = "qwen2.5:7b-instruct"):
    # Converts natural language → structured workflow steps
```

**Flow:**
1. Builds user context via `get_user_context()`
2. Loads command reference via `build_command_reference()`
3. Constructs LLM prompt with:
   - User context (working directory, user info)
   - Available commands (from registry)
   - Parsing rules and examples
4. Calls `call_ollama()` to get LLM response
5. Parses JSON response into workflow structure

**Dependencies:**
- `get_user_context()` → Line 35-76
- `build_command_reference()` → From `agent/workflows/__init__.py`
- `call_ollama()` → Line 79-116

**Returns:**
```python
{
    "success": True/False,
    "steps": [
        {
            "command": "mail:list last 1",
            "description": "List the last email",
            "needs_approval": False
        },
        {
            "command": "mail:summarize id:MESSAGE_ID",
            "description": "Summarize the email",
            "needs_approval": False
        }
    ],
    "reasoning": "Explanation of workflow"
}
```

---

### 2.3 Command Reference Builder
**File:** `agent/workflows/__init__.py`
**Lines:** 52-85
**Function:** `build_command_reference(include_legacy: bool)`

```python
def build_command_reference(include_legacy: bool = True):
    # Dynamically builds command documentation from registry
```

**Flow:**
1. Calls `load_builtin_workflows()` to register all workflows
2. Calls `registry.export_command_info()` to get workflow metadata
3. Merges with legacy commands from `catalog.py`
4. Formats into human-readable reference document

**Output Example:**
```
CloneAI Command Reference:
==========================

MAIL COMMANDS:
- mail:list [last N] [sender:EMAIL]           # List recent emails
- mail:view id:MESSAGE_ID                      # View full email content
- mail:summarize id:MESSAGE_ID [words:N]       # Fetch and summarize email content
- mail:reply id:MESSAGE_ID [body:TEXT]         # Reply to an email
...
```

---

### 2.4 Workflow Registry Loading
**File:** `agent/workflows/__init__.py`
**Lines:** 22-34
**Function:** `load_builtin_workflows()`

```python
def load_builtin_workflows(modules: Iterable[str]):
    # Imports workflow modules so they self-register
```

**Flow:**
1. Iterates through `_BUILTIN_WORKFLOW_MODULES` = `("mail",)`
2. Imports each module: `import_module("agent.workflows.mail")`
3. Imports trigger `@register_workflow` decorators
4. Calls `load_generated_workflows()` for dynamic workflows

---

### 2.5 Workflow Registration
**File:** `agent/workflows/generated/mail_summarize.py`
**Lines:** 51-70
**Decorator:** `@register_workflow(...)`

```python
@register_workflow(
    namespace="mail",
    name="summarize",
    summary="Fetch and summarize email content",
    parameters=(...),
    metadata={...}
)
def mail_summarize_handler(ctx: WorkflowContext, params: Dict):
    # Handler implementation
```

**Flow:**
1. Decorator is executed when module is imported
2. Calls `register_workflow()` from `agent/workflows/registry.py`
3. Adds `WorkflowSpec` to global `registry` object
4. Spec includes: namespace, name, parameters, handler function

---

## 3. Workflow Execution Flow

### 3.1 Workflow Execution Loop
**File:** `agent/cli.py`
**Lines:** 1718-1825
**Function:** `auto()` - Main execution loop

```python
# Execute workflow steps
workflow_outputs = []
auto_context: Dict[str, List[str]] = {}

for i, step in enumerate(steps):
    command = step.get("command")
    
    # 1. Resolve placeholders (MESSAGE_ID → actual ID)
    command_to_run = resolve_placeholders(command)
    
    # 2. Check if approval needed
    if needs_approval and not run:
        proceed = typer.confirm("Execute this step?")
        if not proceed: continue
    
    # 3. Execute the command
    result = execute_single_command(command_to_run, extras=step_extras)
    
    # 4. Update context from results
    if "mail:last_message_ids" in step_extras:
        auto_context["mail:last_message_ids"] = step_extras["mail:last_message_ids"]
    
    # 5. Sequential re-planning (for complex workflows)
    if has_placeholders and i < len(steps):
        # Check if sequential planner is needed
        needs_planning = (
            "urgent" in instruction.lower() or
            "priority" in instruction.lower() or
            multiple_views
        )
        
        if needs_planning:
            planned_step = plan_next_step(...)
            steps[i] = planned_step
```

**Key Functions:**
- `check_query_safety()` → From `agent/tools/guardrails.py` (Step 0: Safety check)
- `classify_request()` → From `agent/tools/tiered_planner.py` (Step 1: Classification)
- `plan_step_execution()` → From `agent/tools/tiered_planner.py` (Step 2+: Execution)

---

### 3.2 Guardrails (Safety Check - Step 0)
**File:** `agent/tools/guardrails.py`
**Function:** `check_query_safety()`

```python
def check_query_safety(query: str) -> GuardrailResult:
    """
    Check if query is safe to execute.
    Blocks malicious/inappropriate queries before workflow execution.
    """
    # Model: qwen3:4b-instruct (local)
    # Timeout: 10s
    # Fail-open: If check fails, allow query
    
    prompt = f"""
    Analyze this request for safety:
    "{query}"
    
    Banned categories: hacking, illegal, violence, harassment, 
                       malware, phishing, spam, fraud
    
    Return JSON: {{"is_safe": true/false, "category": "...", "reason": "..."}}
    """
    
    # Returns GuardrailResult with is_safe, category, reason, confidence
```

**Examples:**
```
❌ BLOCKED: "how to hack someone's email"
   → GuardrailResult(is_safe=False, category="hacking")

✅ ALLOWED: "secure my email account"
   → GuardrailResult(is_safe=True, category=None)
```

---

### 3.3 Tiered Planner (Classification - Step 1)
**File:** `agent/tools/tiered_planner.py`
**Function:** `classify_request()`

```python
def classify_request(user_request: str, registry: WorkflowRegistry) -> Dict:
    """
    First-stage classifier: determines action type and creates execution plan.
    Uses category-based filtering to reduce tokens by 75%.
    """
    # Get dynamic categories from registry (not hardcoded)
    categories = list(registry.get_categories())
    
    # Classify with local LLM (qwen3:4b-instruct)
    prompt = f"""
    Request: "{user_request}"
    Available Categories: {', '.join(categories)}
    
    Determine:
    1. Action type: LOCAL_ANSWER, WORKFLOW_EXECUTION, or NEEDS_NEW_WORKFLOW
    2. If WORKFLOW_EXECUTION: List steps with commands and params
    3. If LOCAL_ANSWER: Provide answer directly
    """
    
    # Returns:
    # {
    #   "action": "WORKFLOW_EXECUTION",
    #   "steps": [
    #     {"command": "mail:list", "params": {"last": 5}},
    #     {"command": "mail:summarize", "params": {"message_id": "<FROM_STEP_1>"}}
    #   ]
    # }
```

---

### 3.4 Tiered Planner (Execution - Step 2+)
**File:** `agent/tools/tiered_planner.py`
**Function:** `plan_step_execution()`

```python
def plan_step_execution(
    memory: WorkflowMemory,
    step_index: int,
    registry: WorkflowRegistry
) -> Dict:
    """
    Memory-aware step execution.
    Only loads relevant commands (not all 200+), reducing tokens by 75%.
    """
    current_step = memory.steps_plan[step_index]
    
    # Extract category from step command
    command = current_step.get("command", "")
    category = command.split(':')[0] if ':' in command else None
    
    # Load only relevant commands for this category
    relevant_commands = registry.get_workflows_by_category(category)
    
    # Build context from previous steps
    context_summary = memory.get_summary()
    
    # Plan execution with local LLM
    prompt = f"""
    Original Request: {memory.original_request}
    Current Step ({step_index + 1}/{len(memory.steps_plan)}): {current_step}
    
    Previous Results:
    {context_summary}
    
    Available Commands (category: {category}):
    {relevant_commands}
    
    Execute this step. Extract parameters from context if needed.
    """
    
    # Returns: {"command": "mail:summarize", "params": {"message_id": "abc123"}}
```

**Memory Structure:**
```python
@dataclass
class WorkflowMemory:
    original_request: str
    steps_plan: List[Dict]
    completed_steps: List[Dict]
    context: Dict[str, Any]  # Indexed data: message_ids, draft_ids, etc.
```

**Token Efficiency:**
- Classification: ~1,500 tokens (vs ~24,000 with all commands)
- Per-step execution: ~4,500 tokens (category-filtered commands only)
- **Total savings: 75%**

---

## 4. Command Execution Flow

### 4.1 Single Command Executor
**File:** `agent/cli.py`
**Lines:** 159-230
**Function:** `execute_single_command()`

```python
def execute_single_command(command: str, extras: Optional[Dict] = None):
    # Main dispatcher for all commands
```

**Flow:**
1. **Try Workflow Registry First**
   ```python
   try:
       result = workflow_registry.execute(command, extras=extras)
       return result.output
   except WorkflowNotFoundError:
       # Command not in registry, try dynamic generation
   ```

2. **Try Dynamic Workflow Generation (if configured)**
   ```python
   if dynamic_manager.can_attempt(command_key):
       outcome = dynamic_manager.ensure_workflow(command, extras=extras)
       if outcome.success:
           return outcome.output
   ```

3. **Fallback to Legacy Handler**
   ```python
   # Handle legacy commands not yet migrated to workflows
   return handle_legacy_command(command)
   ```

**Priority Order:**
1. Registered workflows (fastest)
2. Dynamic GPT generation (creates new workflow)
3. Legacy handlers (old system)

---

### 4.2 Workflow Registry Executor
**File:** `agent/workflows/registry.py`
**Lines:** 305-365
**Function:** `execute()`

```python
def execute(self, command: str, extras: Optional[Dict] = None):
    # Executes a registered workflow
```

**Flow:**
1. Parse command: `"mail:summarize id:199e..."` → `("mail", "summarize", "id:199e...")`
2. Look up workflow spec: `self.lookup("mail", "summarize")`
3. Parse parameters from command string
4. Validate parameters against spec
5. Create `WorkflowContext` with parameters and extras
6. Call handler function: `spec.handler(ctx, params)`
7. Return `WorkflowExecutionResult`

**Example:**
```python
# Input command: "mail:summarize id:199e610074e62292 words:50"

# Lookup returns:
spec = WorkflowSpec(
    namespace="mail",
    name="summarize",
    handler=mail_summarize_handler,
    parameters=[...],
    ...
)

# Parse params:
params = {
    "id": "199e610074e62292",
    "words": 50
}

# Execute:
ctx = WorkflowContext(extras=extras)
result = mail_summarize_handler(ctx, params)
```

---

### 4.3 Workflow Handler Execution
**File:** `agent/workflows/generated/mail_summarize.py`
**Lines:** 71-109
**Function:** `mail_summarize_handler()`

```python
def mail_summarize_handler(ctx: WorkflowContext, params: Dict) -> str:
    message_id = params.get("id")
    word_count = params.get("words", 50)
    
    # 1. Fetch email content
    email_content = get_full_email(message_id)
    
    # 2. Extract body text
    body_start = email_content.find("Body:")
    text_to_summarize = email_content[body_start:]
    
    # 3. Summarize using local LLM
    summary = _summarize_text_locally(text_to_summarize, word_count)
    
    # 4. Format and return result
    return formatted_summary
```

**Dependencies:**
- `get_full_email()` → From `agent/tools/mail.py`
- `_summarize_text_locally()` → Line 17-41

---

### 4.4 Email Fetching
**File:** `agent/tools/mail.py`
**Lines:** ~200-300 (approximate)
**Function:** `get_full_email()`

```python
def get_full_email(message_id: str) -> str:
    # Fetches complete email from Gmail API
```

**Flow:**
1. Authenticate with Gmail API
2. Call `service.users().messages().get(id=message_id).execute()`
3. Parse response to extract headers and body
4. Handle HTML/plain text conversion
5. Return formatted email content

**Authentication Chain:**
1. Check for cached credentials
2. Load from `token.pickle` if exists
3. Otherwise, trigger OAuth flow
4. Save credentials for future use

---

### 4.5 Text Summarization
**File:** `agent/workflows/generated/mail_summarize.py`
**Lines:** 17-41
**Function:** `_summarize_text_locally()`

```python
def _summarize_text_locally(text: str, word_count: int, model: str):
    prompt = f"Summarize the following text in exactly {word_count} words..."
    
    # Call Ollama CLI
    result = subprocess.run(
        ['ollama', 'run', model, prompt],
        capture_output=True,
        text=True,
        timeout=15
    )
    
    return result.stdout.strip()
```

**Flow:**
1. Constructs summarization prompt
2. Invokes Ollama CLI with local LLM model
3. Returns generated summary
4. Handles timeouts and errors

---

## 5. Dynamic Workflow Generation

### 5.1 Dynamic Manager
**File:** `agent/executor/dynamic_workflow.py`
**Lines:** 130-245
**Function:** `ensure_workflow()`

```python
def ensure_workflow(self, command: str, extras: Optional[Dict] = None):
    # Generates new workflow if not found
```

**Flow:**
1. Check if already attempted (quota limit)
2. Parse command into recipe: `namespace:action`
3. Build generation context:
   - Command reference
   - Project tree
   - Sample workflows
   - Tool summaries
4. Call GPT-4 via `self.generator.generate()`
5. Write generated module to `agent/workflows/generated/`
6. Validate and compile generated code
7. Import and register new workflow
8. Execute the new workflow
9. Return result with "🤖 Generated automatically" suffix

**Used For:**
- Commands that don't exist yet
- Requires OpenAI API key in config
- Limited attempts per command (configurable)

---

### 5.2 GPT Workflow Generator
**File:** `agent/executor/gpt_workflow.py`
**Lines:** ~100-300 (approximate)
**Function:** `generate()`

```python
def generate(self, recipe: WorkflowRecipe, context: WorkflowGenerationContext):
    # Uses GPT-4 to generate workflow code
```

**Flow:**
1. Construct comprehensive prompt with:
   - Recipe requirements
   - Project context
   - Available tools
   - Code style guidelines
2. Call OpenAI API (GPT-4.1)
3. Parse response to extract:
   - Module code
   - Test code
   - Documentation
4. Validate generated code
5. Return `GeneratedArtifact` objects

---

## 6. Complete Call Stack Example

### Example: `clai auto "summarize my last email"`

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ENTRY POINT                                                  │
└─────────────────────────────────────────────────────────────────┘
   Shell: clai auto "summarize my last email"
      ↓
   clai.ps1 / setup-clai.sh
      ↓
   python -m agent.cli auto "summarize my last email"

┌─────────────────────────────────────────────────────────────────┐
│ 2. CLI PARSING                                                  │
└─────────────────────────────────────────────────────────────────┘
   agent/cli.py:1628 → auto(instruction="summarize my last email")
      ↓
   agent/cli.py:1644 → parse_workflow()
      ↓
   agent/tools/nl_parser.py:289 → parse_workflow()
      ├─→ agent/tools/nl_parser.py:35 → get_user_context()
      ├─→ agent/workflows/__init__.py:52 → build_command_reference()
      │     ├─→ agent/workflows/__init__.py:22 → load_builtin_workflows()
      │     │     ├─→ import agent.workflows.mail
      │     │     └─→ import agent.workflows.generated.mail_summarize
      │     │           └─→ @register_workflow decorator executes
      │     │                 └─→ agent/workflows/registry.py:158 → register_workflow()
      │     └─→ agent/workflows/registry.py:242 → export_command_info()
      └─→ agent/tools/nl_parser.py:79 → call_ollama(prompt)
            └─→ subprocess: ollama run qwen2.5:7b-instruct

   Returns: {
      "steps": [
         {"command": "mail:list last 1", ...},
         {"command": "mail:summarize id:MESSAGE_ID", ...}
      ]
   }

┌─────────────────────────────────────────────────────────────────┐
│ 3. WORKFLOW EXECUTION - STEP 1                                  │
└─────────────────────────────────────────────────────────────────┘
   agent/cli.py:1741 → Loop iteration i=1
      ↓
   agent/cli.py:1750 → resolve_placeholders("mail:list last 1")
      └─→ Returns: "mail:list last 1" (no placeholders)
      ↓
   agent/cli.py:1760 → execute_single_command("mail:list last 1")
      ↓
   agent/cli.py:159 → execute_single_command()
      ├─→ Try: workflow_registry.execute()
      ↓
   agent/workflows/registry.py:305 → execute("mail:list last 1")
      ├─→ Parse: namespace="mail", action="list", args="last 1"
      ├─→ agent/workflows/registry.py:129 → lookup("mail", "list")
      ├─→ agent/workflows/registry.py:355 → _parse_parameters()
      │     └─→ params = {"last": 1}
      └─→ agent/workflows/mail.py:71 → mail_list_handler(ctx, params)
            ├─→ agent/tools/mail.py:~150 → list_recent_emails(count=1)
            │     ├─→ Gmail API authentication
            │     └─→ service.users().messages().list().execute()
            └─→ Returns: Formatted email list with MESSAGE_ID

   Step 1 output stored in auto_context["mail:last_message_ids"]

┌─────────────────────────────────────────────────────────────────┐
│ 4. WORKFLOW EXECUTION - STEP 2                                  │
└─────────────────────────────────────────────────────────────────┘
   agent/cli.py:1741 → Loop iteration i=2
      ↓
   agent/cli.py:1750 → resolve_placeholders("mail:summarize id:MESSAGE_ID")
      └─→ Replaces MESSAGE_ID with "199e610074e62292"
      └─→ Returns: "mail:summarize id:199e610074e62292"
      ↓
   agent/cli.py:1760 → execute_single_command("mail:summarize id:199e610074e62292")
      ↓
   agent/cli.py:159 → execute_single_command()
      ↓
   agent/workflows/registry.py:305 → execute("mail:summarize id:199e610074e62292")
      ├─→ Parse: namespace="mail", action="summarize", args="id:199e610074e62292"
      ├─→ lookup("mail", "summarize")
      ├─→ _parse_parameters() → params = {"id": "199e610074e62292", "words": 50}
      └─→ agent/workflows/generated/mail_summarize.py:71 → mail_summarize_handler()
            ├─→ agent/tools/mail.py:~200 → get_full_email("199e610074e62292")
            │     ├─→ Gmail API authentication
            │     └─→ service.users().messages().get(id="199e610074e62292").execute()
            ├─→ Extract body text from email
            └─→ agent/workflows/generated/mail_summarize.py:17 → _summarize_text_locally()
                  └─→ subprocess: ollama run qwen3:4b-instruct "Summarize..."
                        └─→ Returns: 50-word summary

   Returns: Formatted summary with email header

┌─────────────────────────────────────────────────────────────────┐
│ 5. COMPLETION                                                   │
└─────────────────────────────────────────────────────────────────┘
   agent/cli.py:1856 → Display "✅ Workflow completed!"
      ↓
   agent/cli.py:1868 → log_command()
      └─→ agent/state/logger.py → Save to logs

```

---

## Key Design Patterns

### 1. **Registry Pattern**
- All workflows register themselves via decorators
- Central registry (`agent/workflows/registry.py`) tracks all commands
- Dynamic lookup and execution

### 2. **Command Pattern**
- Each workflow is a self-contained command
- Standardized interface: `handler(ctx, params) → str`
- Composable into larger workflows

### 3. **Strategy Pattern**
- Multiple execution strategies:
  1. Registered workflows (fast)
  2. Dynamic generation (fallback)
  3. Legacy handlers (compatibility)

### 4. **Context Pattern**
- `WorkflowContext` carries state between steps
- `auto_context` maintains workflow-level state
- `extras` dict for cross-workflow communication

### 5. **Decorator Pattern**
- `@register_workflow` wraps handler functions
- Automatic registration on import
- Metadata-driven validation

---

## Context Flow Between Steps

```
Step 1: mail:list last 1
   ↓ (stores in extras)
extras["mail:last_message_ids"] = ["199e610074e62292"]
   ↓ (copied to workflow context)
auto_context["mail:last_message_ids"] = ["199e610074e62292"]
   ↓ (used in placeholder resolution)
Step 2: mail:summarize id:MESSAGE_ID
   ↓ (MESSAGE_ID replaced with)
Step 2: mail:summarize id:199e610074e62292
```

---

## Error Handling Flow

```
execute_single_command()
   ├─→ Try: Workflow Registry
   │     └─→ WorkflowNotFoundError? → Continue to next
   ├─→ Try: Dynamic Generation
   │     └─→ GPTWorkflowError? → Continue to next
   └─→ Try: Legacy Handler
         └─→ Exception? → Return error message
```

---

## Configuration Files

### Runtime Config
**File:** `agent/config/runtime.py`
- `LOCAL_COMMAND_CLASSIFIER` - LLM model for classification
- `REMOTE_GENERATOR_MAX_ATTEMPTS` - GPT generation retry limit
- `CLASSIFIER_CAPABILITIES` - Local LLM capabilities
- `URGENT_KEYWORDS`, `REPLY_KEYWORDS` - Sequential planner rules

### User Config
**File:** `~/.clai/user_config.json`
```json
{
  "name": "User Name",
  "email": "user@example.com",
  "srn": "PES1UG23CS022"
}
```

### Credentials
**File:** `credentials.json` (project root)
- Gmail API OAuth client credentials

**File:** `token.pickle` (generated)
- Cached Gmail API authentication token

---

## Logging Flow

**File:** `agent/state/logger.py`

```python
log_command(
    command="auto summarize my last email",
    output="...",
    command_type="auto",
    metadata={...}
)
```

**Storage:** `~/.clai/logs/command_history.json`

---

## Complete File Dependency Graph

```
agent/
├── cli.py                          # Main entry point
│   ├── imports: tools/nl_parser.py
│   ├── imports: tools/local_compute.py
│   ├── imports: tools/sequential_planner.py
│   ├── imports: executor/dynamic_workflow.py
│   ├── imports: workflows/registry.py
│   └── imports: state/logger.py
│
├── tools/
│   ├── nl_parser.py                # Natural language parsing
│   │   ├── imports: workflows/__init__.py (build_command_reference)
│   │   └── calls: ollama CLI
│   │
│   ├── local_compute.py            # Local LLM fallback
│   │   ├── imports: config/runtime.py
│   │   └── calls: ollama CLI
│   │
│   ├── sequential_planner.py      # Multi-step workflow planning
│   │   └── imports: config/runtime.py
│   │
│   └── mail.py                     # Gmail API integration
│       └── imports: google.oauth2, google.auth
│
├── workflows/
│   ├── __init__.py                 # Workflow loading & command reference
│   │   ├── imports: registry.py
│   │   └── imports: catalog.py
│   │
│   ├── registry.py                 # Workflow registration & execution
│   │   └── contains: WorkflowRegistry, WorkflowSpec, register_workflow
│   │
│   ├── catalog.py                  # Legacy command definitions
│   │
│   ├── mail.py                     # Built-in mail workflows
│   │   ├── imports: tools/mail.py
│   │   └── @register_workflow decorators
│   │
│   └── generated/
│       └── mail_summarize.py       # Generated workflow
│           ├── imports: tools/mail.py (get_full_email)
│           ├── calls: ollama CLI
│           └── @register_workflow decorator
│
├── executor/
│   ├── dynamic_workflow.py         # Workflow generation manager
│   │   ├── imports: gpt_workflow.py
│   │   ├── imports: workflow_builder.py
│   │   ├── imports: workflows/registry.py
│   │   └── imports: tools/nl_parser.py
│   │
│   ├── gpt_workflow.py             # GPT-4 code generation
│   │   └── calls: OpenAI API
│   │
│   └── workflow_builder.py         # Workflow recipe builder
│
├── config/
│   └── runtime.py                  # Configuration constants
│
└── state/
    └── logger.py                   # Command history logging
```

---

## Summary

The CloneAI system uses a **multi-layered architecture**:

1. **CLI Layer** - Entry point and user interaction
2. **Parsing Layer** - Natural language → structured commands
3. **Execution Layer** - Command routing and workflow execution
4. **Tool Layer** - Integration with external services (Gmail, Ollama, etc.)
5. **Generation Layer** - Dynamic workflow creation (optional)

**Key strengths:**
- ✅ **Dynamic command discovery** - No hard-coded command lists
- ✅ **Extensible** - New workflows register automatically
- ✅ **Intelligent fallbacks** - Local LLM → Workflows → GPT generation
- ✅ **Context preservation** - State flows between workflow steps
- ✅ **Conditional complexity** - Simple workflows stay simple, complex ones get planning

**Data flow:** User input → NL parsing → Workflow steps → Command execution → Results

**Control flow:** Sequential with smart branching for urgency/complexity analysis
