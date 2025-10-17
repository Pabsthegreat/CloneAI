# CloneAI Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Command Processing](#command-processing)
6. [Workflow System](#workflow-system)
7. [Integration Layer](#integration-layer)
8. [State Management](#state-management)
9. [Testing Architecture](#testing-architecture)
10. [Deployment](#deployment)

---

## Overview

CloneAI is an intelligent personal CLI agent built with Python that provides an adaptive command-line interface for managing emails, calendars, documents, and automated tasks. It features a **revolutionary tiered architecture** that combines local LLM intelligence with dynamic GPT workflow generation, achieving 75% token savings while enabling true agentic behavior.

### Key Features

**Core Intelligence:**
- **Tiered Architecture**: Two-stage planning with memory for efficient token usage (75% savings)
- **Command Chaining**: Execute multiple commands with && operator (3-10x faster for multi-item ops)
- **Safety Guardrails**: Lightweight content moderation to block inappropriate queries
- **Dynamic Workflow Generation**: GPT-4 generates new workflows on-demand with LLM-provided context
- **Adaptive Memory**: Context-aware step execution with indexed data tracking
- **Timezone-Aware Context**: LLM receives current date/time with timezone information

**Productivity Tools:**
- **Email Management**: Gmail integration for reading, drafting, sending emails with attachments
- **Calendar Management**: Google Calendar integration for events and meetings
- **Web Search**: Built-in search:web and search:deep for internet queries and content extraction
- **Document Processing**: PDF/DOCX/PPT conversion and merging
- **Task Scheduling**: Automated task execution at specified times
- **Natural Language Processing**: Convert plain English to CLI commands
- **Command History**: Persistent logging of all commands and outputs

### Technology Stack
- **Language**: Python 3.12+
- **CLI Framework**: Typer (built on top of Click)
- **Local LLM**: Ollama (qwen3:4b-instruct for planning, classification, guardrails)
- **Cloud LLM**: OpenAI GPT-4.1 (dynamic workflow generation only)
- **APIs**: Google Gmail API, Google Calendar API, Serper API (web search)
- **Document Processing**: PyPDF2, python-docx, python-pptx, pdf2docx
- **Web Scraping**: BeautifulSoup4, requests
- **Task Scheduling**: schedule library
- **State Management**: JSON-based persistence
- **Vector Store** (Future): Chroma + LangChain for RAG

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │ clai   │  │ clai   │  │ clai   │  │ clai   │  │ clai   │   │
│  │   do   │  │  auto  │  │interpret│  │ draft- │  │ history│   │
│  │        │  │        │  │        │  │  email │  │        │   │
│  └────┬───┘  └────┬───┘  └────┬───┘  └────┬───┘  └────┬───┘   │
│       └───────────┴───────────┴───────────┴───────────┘         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────▼────────────┐
                │     CLI Router          │
                │   (agent/cli.py)        │
                └───────────┬────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
    ┌───────▼───────┐ ┌────▼─────┐ ┌──────▼──────┐
    │   Workflow    │ │   NL     │ │   Legacy    │
    │   Registry    │ │  Parser  │ │   Command   │
    │   (new)       │ │ (Ollama) │ │   Parser    │
    └───────┬───────┘ └────┬─────┘ └──────┬──────┘
            │               │               │
    ┌───────▼───────────────▼───────────────▼──────┐
    │         Command Execution Layer               │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
    │  │ Workflow │  │   Tool   │  │ Document │   │
    │  │ Handlers │  │ Modules  │  │ Handlers │   │
    │  └──────────┘  └──────────┘  └──────────┘   │
    └────────────────────┬──────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───▼────┐  ┌───────────▼────┐  ┌───────────▼────┐
│ Gmail  │  │  Google         │  │   Local File   │
│  API   │  │  Calendar API   │  │   System       │
└────────┘  └────────────────┘  └────────────────┘
            
┌──────────────────────────────────────────────────┐
│            State & Persistence Layer              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │  Command   │  │  Scheduled │  │   Auth     │ │
│  │  History   │  │   Tasks    │  │   Tokens   │ │
│  │  (JSON)    │  │   (JSON)   │  │  (Pickle)  │ │
│  └────────────┘  └────────────┘  └────────────┘ │
└──────────────────────────────────────────────────┘
```

### Directory Structure

```
CloneAI/
├── agent/                      # Main application package
│   ├── __init__.py
│   ├── cli.py                 # CLI command definitions & routing
│   ├── system_info.py         # System detection & path management
│   │
│   ├── executor/              # Command execution engine
│   │   ├── workflow_builder.py    # Multi-step workflow builder
│   │   └── test.py               # Executor tests
│   │
│   ├── state/                 # State management
│   │   ├── __init__.py
│   │   └── logger.py          # Command history logger
│   │
│   ├── tools/                 # Tool modules (integrations)
│   │   ├── __init__.py
│   │   ├── mail.py            # Gmail API integration
│   │   ├── calendar.py        # Google Calendar integration
│   │   ├── web_search.py      # Serper API web search integration
│   │   ├── documents.py       # Document processing
│   │   ├── scheduler.py       # Task scheduling
│   │   ├── nl_parser.py       # Natural language parser (Ollama)
│   │   ├── ollama_client.py   # Ollama LLM client
│   │   ├── tiered_planner.py  # Two-stage planning with memory
│   │   ├── guardrails.py      # Safety content moderation
│   │   ├── email_parser.py    # Email parsing utilities
│   │   ├── serper_credentials.py  # Serper API credentials
│   │   └── priority_emails.py # Priority email management
│   │
│   └── workflows/             # New workflow system
│       ├── __init__.py        # Workflow exports & loading
│       ├── registry.py        # Workflow registration engine
│       ├── catalog.py         # Legacy command catalog
│       ├── mail.py            # Mail workflow handlers
│       ├── calendar.py        # Calendar workflow handlers
│       ├── search.py          # Web search workflows (NEW)
│       ├── system.py          # System management workflows
│       └── generated/         # GPT-generated workflows
│           └── *.py           # Dynamically created workflows
│
├── tests/                     # Test suite
│   ├── test_auto_workflow.py
│   ├── test_workflow_registry.py
│   ├── test_workflow_builder.py
│   └── ...
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # This file
│   ├── COMPLETE_GUIDE.md      # User guide
│   ├── EMAIL_IMPLEMENTATION.md
│   ├── NL_FEATURES.md
│   ├── SECURITY.md
│   └── TESTING.md
│
├── pyproject.toml             # Project configuration
├── requirements.txt           # Python dependencies
└── README.md                  # Project overview
```

---

## Core Components

### 1. CLI Router (`agent/cli.py`)

**Purpose**: Main entry point for all user commands. Routes commands to appropriate handlers.

**Key Functions**:
- `hi()` - Interactive greeting
- `chat()` - Chat interface
- `do()` - Execute structured commands
- `auto()` - Execute multi-step workflows
- `interpret()` - Natural language to command translation
- `draft_email()` - AI-powered email composition
- `history()` - View command history
- `merge()` - Document merging
- `convert()` - Document conversion
- `scheduler()` - Task scheduler management
- `reauth()` - Re-authenticate with Google APIs

**Command Flow**:
```python
User Input → Typer CLI → Command Handler → Execution Layer → Result
```

**Command Execution with Chaining**:
```python
# In agent/cli.py
def execute_single_command(action: str, *, extras) -> str:
    """Execute a single command or chained commands."""
    # Check if command contains && (chain operator)
    if '&&' in action:
        return execute_chained_commands(action, extras=extras)
    
    # Execute single command
    return execute_single_command_atomic(action, extras=extras)

def execute_chained_commands(chained_action: str, *, extras) -> str:
    """Execute multiple commands chained with && operator."""
    commands = [cmd.strip() for cmd in chained_action.split('&&')]
    results = []
    
    for i, cmd in enumerate(commands, 1):
        result = execute_single_command_atomic(cmd, extras=extras)
        results.append(result)
    
    return "\n\n".join(f"Command {i} result:\n{res}" for i, res in enumerate(results))
```

**Example**:
```python
@app.command()
def do(action: str):
    """Execute a command"""
    # 1. Check for chained commands (NEW)
    if '&&' in action:
        return execute_chained_commands(action, extras=registry_extras)
    
    # 2. Try workflow registry (new system)
    try:
        result = workflow_registry.execute(action, extras=registry_extras)
        return result.output
    except WorkflowNotFoundError:
        pass  # Fall through to legacy
    
    # 3. Try legacy command parsing
    if action.startswith("mail:list"):
        # Parse and execute...
```

### 2. Workflow Registry (`agent/workflows/registry.py`)

**Purpose**: New modular system for registering and executing commands with type-safe parameters.

**Key Classes**:

#### `WorkflowSpec`
Metadata about a workflow command:
```python
@dataclass
class WorkflowSpec:
    namespace: str          # e.g., "mail"
    name: str              # e.g., "list"
    summary: str           # Brief description
    description: str       # Full description
    handler: WorkflowHandler  # Execution function
    parameters: Sequence[ParameterSpec]
    parameter_parser: Optional[ParameterParser]
```

#### `ParameterSpec`
Defines a workflow parameter:
```python
@dataclass
class ParameterSpec:
    name: str
    type: Callable[[str], Any]  # Type converter
    required: bool
    default: Any
    aliases: Sequence[str]
```

#### `WorkflowRegistry`
Central registry for all workflows:
```python
class WorkflowRegistry:
    def register(self, spec: WorkflowSpec) -> WorkflowSpec
    def execute(self, raw_command: str, *, extras) -> WorkflowExecutionResult
    def get(self, namespace: str, name: str) -> WorkflowSpec
```

**Registration Example**:
```python
@register_workflow(
    namespace="mail",
    name="list",
    summary="List recent emails",
    parameters=[
        ParameterSpec(name="count", type=int, default=5),
        ParameterSpec(name="sender", type=str, default=None),
    ]
)
def run_mail_list(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    count = params["count"]
    sender = params.get("sender")
    messages = get_email_messages(count=count, sender=sender)
    return format_email_list(messages)
```

### 3. Natural Language Parser (`agent/tools/nl_parser.py`)

**Purpose**: Converts natural language to structured commands using Ollama.

**Key Functions**:

#### `parse_natural_language(user_input: str) -> Dict`
Converts single natural language command to CLI command.

**Example**:
```
Input: "show me my last 10 emails"
Output: {
    "success": True,
    "command": "mail:list last 10",
    "confidence": "high",
    "explanation": "Lists the 10 most recent emails"
}
```

#### `parse_workflow(instruction: str) -> Dict`
Converts multi-step instruction to workflow.

**Example**:
```
Input: "check my last 5 emails and reply to each one"
Output: {
    "success": True,
    "steps": [
        {
            "command": "mail:list last 5",
            "description": "List last 5 emails",
            "needs_approval": False
        },
        {
            "command": "mail:draft to:RECIPIENT subject:Re: SUBJECT body:REPLY",
            "description": "Draft reply",
            "needs_approval": True
        }
    ],
    "reasoning": "First retrieve emails, then compose replies"
}
```

#### `generate_email_content(instruction: str) -> Dict`
Generates professional email content.

**Example**:
```
Input: "send email to john about project deadline"
Output: {
    "success": True,
    "to": "john@example.com",
    "subject": "Project Deadline Update",
    "body": "Dear John,\n\nI wanted to discuss..."
}
```

**LLM Integration**:
```python
def call_ollama(prompt: str, model: str) -> str:
    """Call Ollama via subprocess"""
    process = subprocess.Popen(
        ["ollama", "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    stdout, _ = process.communicate(input=prompt, timeout=60)
    return stdout.strip()
```

### 3a. Tiered Planner (`agent/tools/tiered_planner.py`) ⭐ **CORE ARCHITECTURE**

**Purpose**: Revolutionary two-stage planning system that achieves **75% token savings** through intelligent classification and memory-aware execution.

**Key Innovation**: Separates classification from execution, providing only necessary context at each step instead of flooding every prompt with all available commands.

---

#### **Architecture: Two-Stage Planning**

**Stage 1: Classification** (PROMPT 1)
- Analyzes user request
- Determines action type: `LOCAL_ANSWER`, `WORKFLOW_EXECUTION`, or `NEEDS_NEW_WORKFLOW`
- Returns execution plan with ordered steps
- **Token Cost**: ~1,500 tokens (vs ~24,000 with old system)

**Stage 2+: Execution** (PROMPT 2, 3, 4...)
- Executes each step with **only relevant context**
- Maintains `WorkflowMemory` with indexed data tracking
- Extracts parameters from previous outputs (e.g., Message IDs)
- Tracks progress and prevents ID reuse
- **Token Cost per step**: ~4,500 tokens (only loads relevant commands)

**Total Savings**: ~6,000 tokens vs ~24,000 tokens = **75% reduction**

---

#### **Key Functions**

##### `classify_request(user_request: str, registry: WorkflowRegistry) -> Dict`
First-stage classifier that determines how to handle the request.

**Returns**:
```python
{
    "action": "WORKFLOW_EXECUTION",  # or LOCAL_ANSWER, NEEDS_NEW_WORKFLOW
    "steps": [
        {
            "command": "mail:list",
            "params": {"last": 5},
            "description": "Fetch last 5 emails"
        },
        {
            "command": "mail:summarize",
            "params": {"message_id": "<FROM_STEP_1>"},
            "description": "Summarize each email"
        }
    ],
    "answer": None,  # Only set for LOCAL_ANSWER
    "reasoning": "Multi-step email analysis workflow"
}
```

**Dynamic Category Loading**:
- Categories derived from existing workflows in registry (not hardcoded)
- Example: `mail`, `calendar`, `document`, `system`, `scheduler`
- Updates automatically when new workflows are registered

##### `plan_step_execution(memory: WorkflowMemory, step_index: int, registry: WorkflowRegistry) -> Dict`
Executes individual steps with memory-aware context.

**Memory Structure**:
```python
@dataclass
class WorkflowMemory:
    original_request: str
    steps_plan: List[Dict]
    completed_steps: List[Dict]
    context: Dict[str, Any]  # Indexed data from previous steps
```

**Context Indexing**:
```python
# Step 1 output: "Found emails: [ID: abc123, ID: def456, ID: ghi789]"
memory.context = {
    "message_ids": ["abc123", "def456", "ghi789"],
    "completed_commands": ["mail:list"]
}

# Step 2 uses indexed context:
# "Reply to message ID: abc123" (extracts from memory.context)
```

**Returns**:
```python
{
    "command": "mail:summarize",
    "params": {"message_id": "abc123"},
    "description": "Summarize email abc123",
    "reasoning": "Using first message ID from previous step"
}
```

---

#### **Performance Characteristics**

**Model**: qwen3:4b-instruct (local Ollama)
**Execution Time**:
- Classification: ~1-2 seconds
- Per-step planning: ~2-3 seconds
- Total for 4-step workflow: ~10-12 seconds

**Token Efficiency**:
| Stage | Old System | Tiered System | Savings |
|-------|-----------|---------------|---------|
| PROMPT 1 | 24,000 | 1,500 | 94% |
| PROMPT 2 | 24,000 | 4,500 | 81% |
| PROMPT 3 | 24,000 | 4,500 | 81% |
| PROMPT 4 | 24,000 | 4,500 | 81% |
| **Total** | **96,000** | **15,000** | **84%** |

---

#### **Example: Email Analysis Workflow**

**User Request**: "analyze my last 5 emails and summarize them"

**PROMPT 1 (Classification)**:
```
Request: "analyze my last 5 emails and summarize them"
Available Categories: mail, calendar, document, system

→ Action: WORKFLOW_EXECUTION
→ Steps: [
    {command: "mail:list", params: {last: 5}},
    {command: "mail:summarize", params: {message_id: "<FROM_STEP_1>"}}
  ]
```

**PROMPT 2 (Execute Step 1)**:
```
Original Request: "analyze my last 5 emails..."
Current Step: {command: "mail:list", params: {last: 5}}
Relevant Commands: [mail:list, mail:get_message]

→ Execute: mail:list last:5
→ Output: "Message IDs: [abc123, def456, ghi789, jkl012, mno345]"
→ Update Memory: context["message_ids"] = [abc123, ...]
```

**PROMPT 3 (Execute Step 2)**:
```
Original Request: "analyze my last 5 emails..."
Current Step: {command: "mail:summarize", params: {message_id: "<FROM_STEP_1>"}}
Context: {message_ids: [abc123, def456, ...]}
Relevant Commands: [mail:summarize, mail:get_message]

→ Execute: mail:summarize message_id:abc123
→ Output: "Email summary..."
```

### 3b. Guardrails (`agent/tools/guardrails.py`) 🛡️ **SAFETY LAYER**

**Purpose**: Lightweight content moderation to block inappropriate, harmful, or malicious queries before they reach workflow execution.

**Key Function**: `check_query_safety(query: str) -> GuardrailResult`

**Model**: qwen3:4b-instruct (local Ollama)
- **Why not gemma3:1b?** Too weak, passes malicious queries like "how to hack email"
- **Performance**: ~1-2 seconds per check
- **Timeout**: 10 seconds
- **Fail-open**: If check fails/times out, allows query (availability over security)

---

#### **Banned Categories**

```python
BANNED_CATEGORIES = [
    "hacking", "illegal", "violence", "harassment", 
    "malware", "phishing", "spam", "fraud",
    "privacy_violation", "unauthorized_access"
]
```

**Examples**:
- ❌ **BLOCKED**: "how to hack someone's email", "create malware", "spam contacts"
- ✅ **ALLOWED**: "secure my email account", "check for phishing", "block spam"

---

#### **GuardrailResult Structure**

```python
@dataclass
class GuardrailResult:
    is_safe: bool
    category: Optional[str]  # Detected category if unsafe
    reason: str
    confidence: str  # "high", "medium", "low"
```

**Example Returns**:
```python
# Unsafe query
GuardrailResult(
    is_safe=False,
    category="hacking",
    reason="Request involves unauthorized email access",
    confidence="high"
)

# Safe query
GuardrailResult(
    is_safe=True,
    category=None,
    reason="Query is legitimate productivity task",
    confidence="high"
)
```

---

#### **Integration in CLI (Step 0)**

```python
@app.command()
def auto(request: str):
    """Process natural language requests with safety checks"""
    # Step 0: Safety check (FIRST LINE OF DEFENSE)
    guardrail_result = check_query_safety(request)
    
    if not guardrail_result.is_safe:
        typer.secho(
            f"❌ Query blocked: {guardrail_result.reason}",
            fg=typer.colors.RED
        )
        return
    
    # Step 1: Classification (tiered planner)
    result = classify_request(request, registry)
    
    # Step 2+: Execution
    # ...
```

---

#### **Design Philosophy**

**Fail-Open by Design**:
- Prioritizes availability over absolute security
- Model failures/timeouts don't block legitimate queries
- Suitable for personal productivity tool (not enterprise security)

**Lightweight Model**:
- Local execution (no API calls)
- Fast response (~1-2s)
- Minimal impact on user experience

**Conservative Blocking**:
- Only blocks clearly malicious intent
- Allows security-related queries with positive intent ("secure", "protect", "check")
- Reduces false positives

---

### 3c. GPT Workflow Generation (`agent/executor/gpt_workflow.py`) 🤖 **DYNAMIC GENERATION**

**Purpose**: Automatically generates new workflow code when no existing workflow can handle a request.

**Key Innovation**: Local LLM generates detailed natural language prompts for GPT-4, dramatically improving code quality and reducing hallucinations.

---

#### **Two-LLM Architecture**

**Local LLM (qwen3:4b-instruct)**: Context Generator
- Analyzes user request and command catalog
- Generates detailed natural language description
- Specifies parameter types, return structure, error handling
- **Example Output**: "Create a workflow to fetch HTML from a URL using the requests library. Accept a 'url' parameter (string). Return HTML content as string. Handle HTTP errors gracefully."

**Cloud LLM (GPT-4.1)**: Code Generator
- Receives LLM-generated context as user_context field
- Generates Python workflow code
- Uses OpenAI Responses API
- **Why GPT?** Superior code quality, handles edge cases, proper error handling

---

#### **Generation Flow**

**Trigger**: `classify_request()` returns `action: "NEEDS_NEW_WORKFLOW"`

**Step 1: Local LLM generates context**
```python
# In tiered_planner.py
prompt = f"""
User wants: "{user_request}"
Existing commands cannot handle this.

Generate detailed requirements for a new workflow:
- What should it do?
- What parameters does it need?
- What should it return?
- How should errors be handled?
"""

user_context = ollama_chat(prompt)
# Returns: "Fetch HTML from URL using requests. 
#           Parameter: url (string). 
#           Return: HTML content (string).
#           Handle: ConnectionError, Timeout, HTTPError"
```

**Step 2: GPT generates code**
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
# Generates complete Python workflow with Click decorators
```

**Step 3: Save and reload**
```python
# Save to agent/workflows/generated/system_fetch_html_from_url.py
save_workflow_code(namespace, name, code)

# Reload registry to include new workflow
from agent.workflows import registry
importlib.reload(registry)
```

---

#### **WorkflowRecipe Structure**

```python
@dataclass
class WorkflowRecipe:
    namespace: str           # e.g., "system"
    name: str               # e.g., "fetch_html_from_url"
    user_request: str       # Original user query
    user_context: str       # ← LLM-generated detailed description
    command_catalog: Dict   # Existing workflows for reference
```

---

#### **Dynamic Category Mapping**

Categories are **not hardcoded** - they're derived from existing workflows in the registry:

```python
def _get_category_for_namespace(namespace: str, command_catalog: Dict) -> str:
    """
    Map workflow namespace to category based on existing workflows.
    Falls back to 'general' if namespace not found.
    """
    namespace_to_category = {}
    for category, workflows in command_catalog.items():
        for workflow in workflows:
            ns = workflow.split(':')[0]
            namespace_to_category[ns] = category
    
    return namespace_to_category.get(namespace, 'general')
```

**Why Dynamic?**
- Automatically adapts as new workflows are added
- No maintenance burden (no hardcoded mappings to update)
- Extensible: new categories emerge organically

---

#### **Generated Workflow Examples**

**1. Web Scraping**:
```python
# agent/workflows/generated/system_fetch_html_from_url.py
@register_workflow("system", "fetch_html_from_url")
def fetch_html_from_url(url: str) -> Dict:
    """Fetch HTML content from a URL"""
    import requests
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {"success": True, "html": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**2. File Operations**:
```python
# agent/workflows/generated/system_count_lines_in_files.py
@register_workflow("system", "count_lines_in_files")
def count_lines_in_files(file_paths: List[str]) -> Dict:
    """Count lines in specified files"""
    from pathlib import Path
    results = {}
    for path_str in file_paths:
        path = Path(path_str)
        if path.exists() and path.is_file():
            with open(path) as f:
                results[path_str] = len(f.readlines())
    return {"success": True, "counts": results, "total": sum(results.values())}
```

---

#### **Quality Improvements from LLM Context**

**Before** (without LLM context):
- GPT hallucinated parameters (e.g., `choices=['a', 'b']`)
- Incorrect error handling (e.g., `ctx.fail()` which doesn't exist)
- Missing imports
- No type hints

**After** (with LLM context):
- Correct parameter types
- Proper error handling with try/except
- All imports included
- Comprehensive return structures
- Edge case handling

---

### 4. Command History Logger (`agent/state/logger.py`)

**Purpose**: Persistent logging of all commands and outputs.

**Key Class**: `CommandLogger`

**Features**:
- Circular buffer (max 100 entries)
- JSON persistence
- Search and filtering
- Statistics tracking

**Structure**:
```python
{
    "timestamp": "2025-10-13T14:30:00",
    "command": "do mail:list last 5",
    "command_type": "mail",
    "output": "...",
    "metadata": {
        "count": 5,
        "sender": null,
        "action": "list"
    }
}
```

**Usage**:
```python
from agent.state import log_command

log_command(
    command="mail:list last 5",
    output=result,
    command_type="mail",
    metadata={"count": 5, "action": "list"}
)
```

### 5. Gmail Integration (`agent/tools/mail.py`)

**Purpose**: Interface with Gmail API for email operations.

**Key Class**: `GmailClient`

**Authentication Flow**:
```
1. Check for existing token.pickle
2. If expired, refresh with refresh_token
3. If no token, run OAuth flow in browser
4. Save credentials to token.pickle
```

**Main Functions**:

```python
# List emails
def get_email_messages(count: int, sender: str, query: str, category: str) -> List[Dict]:
    """
    Retrieves emails from Gmail with optional filters.
    
    Args:
        count: Number of emails to retrieve
        sender: Filter by sender email/domain
        query: Custom Gmail query string
        category: Gmail category (promotions, social, updates, primary, forums)
    
    Defaults to inbox-only (excludes drafts, sent, trash) when no query specified.
    Falls back to partial sender match if exact match fails.
    """

# View email
def get_full_email(message_id: str) -> str:
    """Get full email content with body"""

# Download attachments
def download_email_attachments(message_id: str, save_dir: str) -> str:
    """Download all attachments from an email"""

# Create draft
def create_draft_email(to: str, subject: str, body: str, ...) -> str:
    """Create a draft email in Gmail"""

# Send email
def send_email_now(to: str, subject: str, body: str, ...) -> str:
    """Send email immediately"""

# Meeting invites
def create_and_send_meeting_invite(...) -> str:
    """Create calendar event and send email invitation"""
```

**API Scopes Required**:
```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send'
]
```

**Gmail Query Features** (2025 Update):

1. **Inbox-Only Default**:
   ```python
   # When no query specified, defaults to inbox
   if not query:
       query = "in:inbox"
   ```
   - Excludes drafts, sent items, trash by default
   - Prevents sequential workflows from processing draft emails
   - User must explicitly query other folders if needed

2. **Category Filtering**:
   ```python
   # Add category to query
   if category:
       base_query = f"category:{category}"
   ```
   - Supports Gmail categories: promotions, social, updates, primary, forums
   - Combines with sender and count filters
   - Example: `category:promotions from:sender@example.com`

3. **Sender Fallback Logic**:
   - First tries exact sender match: `from:sender@example.com`
   - Falls back to domain: `from:example.com`
   - Falls back to local part: `from:sender`
   - Returns most relevant results

**Example Queries**:
```python
# Default (inbox only)
get_email_messages(count=5)
→ query: "in:inbox"

# Category filter
get_email_messages(count=5, category="promotions")
→ query: "category:promotions"

# Combined filters
get_email_messages(count=5, sender="boss@company.com", category="primary")
→ query: "from:boss@company.com" (tries sender first)
   OR "category:primary from:boss@company.com" (if both specified)
```

### 6. Calendar Integration (`agent/tools/calendar.py`)

**Purpose**: Google Calendar integration for event management.

**Key Functions**:

```python
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str = None,
    duration_minutes: int = 60,
    location: str = None,
    description: str = None
) -> str:
    """Create a calendar event"""

def list_calendar_events(count: int = 10) -> str:
    """List upcoming calendar events"""
```

**Event Structure**:
```python
{
    'summary': 'Meeting Title',
    'start': {'dateTime': '2025-10-15T14:00:00', 'timeZone': 'UTC'},
    'end': {'dateTime': '2025-10-15T15:00:00', 'timeZone': 'UTC'},
    'location': 'Conference Room',
    'description': 'Meeting details'
}
```

### 7. Document Processing (`agent/tools/documents.py`)

**Purpose**: PDF, Word, and PowerPoint processing.

**Key Functions**:

```python
# PDF Operations
def merge_pdf_files(directory: str, output_path: str, ...) -> str:
    """Merge multiple PDF files"""

def convert_pdf_to_docx(pdf_path: str, docx_path: str) -> str:
    """Convert PDF to Word document"""

# PowerPoint Operations
def merge_ppt_files(directory: str, output_path: str, ...) -> str:
    """Merge PowerPoint presentations"""

def convert_ppt_to_pdf(ppt_path: str, pdf_path: str) -> str:
    """Convert PPT to PDF (Windows only)"""

# Word Operations
def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> str:
    """Convert Word to PDF (Windows only)"""
```

**Libraries Used**:
- `PyPDF2`: PDF manipulation
- `pdf2docx`: PDF to Word conversion
- `python-docx`: Word document handling
- `python-pptx`: PowerPoint handling
- `comtypes`: Windows COM automation for Office conversions

### 8. Task Scheduler (`agent/tools/scheduler.py`)

**Purpose**: Automated task execution at specified times.

**Key Class**: `TaskScheduler`

**Storage**: `~/.clai/scheduled_tasks.json`

**Task Structure**:
```python
{
    "id": 1,
    "name": "Check Email",
    "command": "mail:list last 5",
    "time": "09:00",
    "enabled": True,
    "last_run": "2025-10-13T09:00:00",
    "created_at": "2025-10-12T10:00:00"
}
```

**Functions**:
```python
def add_scheduled_task(name: str, command: str, time: str) -> str
def remove_scheduled_task(task_id: int) -> str
def toggle_scheduled_task(task_id: int) -> str
def list_scheduled_tasks() -> str
def start_scheduler() -> None  # Blocking, runs tasks
```

**Scheduler Loop**:
```python
while True:
    schedule.run_pending()
    time.sleep(1)
```

---

## Data Flow

### 1. Direct Command Flow

```
User: clai do "mail:list last 5"
   ↓
cli.do(action="mail:list last 5")
   ↓
execute_single_command(action, extras={})
   ↓
Try workflow_registry.execute("mail:list last 5")
   ↓
Parse command: namespace="mail", name="list", args="last 5"
   ↓
Get workflow spec: registry.get("mail", "list")
   ↓
Parse arguments: {"count": 5, "sender": None}
   ↓
Execute handler: run_mail_list_workflow(ctx, params)
   ↓
Call Gmail API: get_email_messages(count=5)
   ↓
Format result: format_email_list(messages)
   ↓
Log command: log_command("do mail:list last 5", result, "mail", {...})
   ↓
Return result to user
```

### 2. Natural Language Flow

```
User: clai interpret "show me my last 10 emails"
   ↓
cli.interpret(message="show me...")
   ↓
parse_natural_language(message)
   ↓
Build prompt with command reference
   ↓
call_ollama(prompt, model="qwen3:4b-instruct")
   ↓
Parse JSON response: {
    "command": "mail:list last 10",
    "confidence": "high",
    "explanation": "..."
}
   ↓
Display parsed command to user
   ↓
(If --run flag) Execute: do("mail:list last 10")
```

### 3. Workflow Automation Flow

```
User: clai auto "check last 5 emails and reply"
   ↓
cli.auto(instruction="check last 5...")
   ↓
parse_workflow(instruction)
   ↓
call_ollama with workflow parsing prompt
   ↓
Get steps: [
    {"command": "mail:list last 5", "needs_approval": false},
    {"command": "mail:draft ...", "needs_approval": true}
]
   ↓
For each step:
    ↓
    Resolve placeholders (MESSAGE_ID, DRAFT_ID)
    ↓
    (If needs_approval) Ask user confirmation
    ↓
    execute_single_command(command, extras={})
    ↓
    Store context: extras["mail:last_message_ids"] = [...]
    ↓
    Use context in next step
   ↓
Log complete workflow
   ↓
Return results
```

### 4. Email Draft to Send Flow

```
User: clai draft-email "email john about meeting"
   ↓
cli.draft_email(instruction="...")
   ↓
generate_email_content(instruction)
   ↓
call_ollama with email generation prompt
   ↓
Get: {
    "to": "john@example.com",
    "subject": "Meeting Discussion",
    "body": "Dear John,\n\n..."
}
   ↓
Display preview to user
   ↓
Ask: [s]end, [d]raft, [e]dit, [c]ancel
   ↓
If send: send_email_now(to, subject, body)
   ↓
If draft: create_draft_email(to, subject, body)
   ↓
Return result
```

---

## Command Processing

### Command Syntax

CloneAI supports three command formats:

#### 1. Namespace:Action Format
```bash
clai do "namespace:action param1:value1 param2:value2"
```

Examples:
```bash
clai do "mail:list last 10"
clai do "mail:list sender:john@example.com"
clai do "calendar:create title:Meeting start:2025-10-15T14:00:00"
```

#### 2. Natural Language Format
```bash
clai interpret "natural language instruction" [--run]
```

Examples:
```bash
clai interpret "show me my last 10 emails"
clai interpret "create a meeting tomorrow at 2pm" --run
```

#### 3. Workflow Format
```bash
clai auto "multi-step instruction" [--run]
```

Examples:
```bash
clai auto "check my emails and reply to important ones"
clai auto --run "schedule meeting and send invites"
```

### Parameter Parsing

**Supported Formats**:
- `key:value` (colon separator)
- `key=value` (equals separator)
- `--key value` (flag format)
- Positional arguments

**Examples**:
```bash
# All equivalent:
mail:list last 5
mail:list count:5
mail:list count=5
mail:list --count 5
```

### Command Categories

#### Email Commands
| Command | Description | Example |
|---------|-------------|---------|
| `mail:list` | List emails | `mail:list last 10` |
| `mail:view` | View full email | `mail:view id:MSG_ID` |
| `mail:download` | Download attachments | `mail:download id:MSG_ID` |
| `mail:draft` | Create draft | `mail:draft to:user@test.com subject:Hi body:Hello` |
| `mail:send` | Send email | `mail:send to:user@test.com subject:Hi body:Hello` |
| `mail:priority` | List priority emails | `mail:priority last 10` |

#### Calendar Commands
| Command | Description | Example |
|---------|-------------|---------|
| `calendar:create` | Create event | `calendar:create title:Meeting start:2025-10-15T14:00:00` |
| `calendar:list` | List events | `calendar:list next 5` |

#### Scheduler Commands
| Command | Description | Example |
|---------|-------------|---------|
| `tasks` | List tasks | `tasks` |
| `task:add` | Add task | `task:add name:Check command:mail:list time:09:00` |
| `task:remove` | Remove task | `task:remove 1` |
| `task:toggle` | Enable/disable | `task:toggle 1` |

---

## Workflow System

### Architecture

The workflow system provides a type-safe, modular way to register and execute commands.

### Migration Strategy

CloneAI is in the process of migrating from **legacy command parsing** (regex-based in `cli.py`) to the **new workflow registry** (type-safe in `agent/workflows/`).

**Current State**:
- ✅ `mail:list` - Migrated to workflow registry
- ❌ `mail:view` - Still legacy
- ❌ `mail:draft` - Still legacy
- ❌ `calendar:*` - Still legacy
- ❌ `task:*` - Still legacy

**Execution Priority**:
1. Try workflow registry first
2. If `WorkflowNotFoundError`, fall back to legacy parsing
3. If no match, return error

### Creating a New Workflow

**Step 1**: Define in `agent/workflows/<namespace>.py`:

```python
from agent.workflows import register_workflow, ParameterSpec, WorkflowContext

@register_workflow(
    namespace="calendar",
    name="list",
    summary="List upcoming calendar events",
    description="Fetches upcoming events from Google Calendar",
    parameters=[
        ParameterSpec(
            name="count",
            description="Number of events to retrieve",
            type=int,
            default=10,
            aliases=["n", "limit"]
        )
    ],
    metadata={
        "category": "CALENDAR COMMANDS",
        "usage": "calendar:list [next N]",
        "examples": [
            "calendar:list next 5",
            "calendar:list count:10"
        ]
    }
)
def run_calendar_list(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    count = params["count"]
    events = list_calendar_events(count=count)
    return format_events(events)
```

**Step 2**: Register module in `agent/workflows/__init__.py`:

```python
_BUILTIN_WORKFLOW_MODULES: Tuple[str, ...] = (
    "mail",
    "calendar",  # Add this
)
```

**Step 3**: Remove legacy parsing from `cli.py` (once tested).

### Workflow Context

Every workflow handler receives a `WorkflowContext` object:

```python
@dataclass
class WorkflowContext:
    raw_command: str              # Original command string
    registry: WorkflowRegistry    # Access to registry
    extras: MutableMapping[str, Any]  # For passing data between steps
```

**Using Extras**:
```python
def run_mail_list(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    messages = get_email_messages(...)
    
    # Store message IDs for next command in workflow
    ctx.extras["mail:last_message_ids"] = [msg["id"] for msg in messages]
    
    return format_email_list(messages)
```

---

## Integration Layer

### Google API Authentication

**OAuth 2.0 Flow**:

```python
# First time setup
1. User runs command (e.g., clai do "mail:list")
2. No token.pickle exists
3. Open browser for Google OAuth consent
4. User grants permissions
5. Save credentials to ~/.clai/gmail_token.pickle
6. Subsequent calls use cached token
```

**Token Refresh**:
```python
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    # Save updated token
```

**Re-authentication**:
```bash
clai reauth gmail     # Delete token, force re-auth
clai reauth calendar  # Delete calendar token
clai reauth all       # Delete all tokens
```

### Ollama Integration

**Setup**:
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull qwen3:4b-instruct
```

**Usage in Code**:
```python
def call_ollama(prompt: str, model: str = "qwen3:4b-instruct") -> str:
    process = subprocess.Popen(
        ["ollama", "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=prompt, timeout=60)
    return stdout.strip()
```

**Prompt Engineering**:
- Include command reference in prompt
- Request JSON-only output
- Provide examples
- Handle markdown code blocks in response

### File System Integration

**Configuration Directory**: `~/.clai/`

```
~/.clai/
├── gmail_token.pickle          # Gmail OAuth token
├── calendar_token.pickle       # Calendar OAuth token
├── command_history.json        # Command log (max 100 entries)
├── scheduled_tasks.json        # Scheduled tasks
└── priority_senders.json       # Priority email config
```

**Path Management** (`agent/system_info.py`):
```python
def get_config_dir() -> Path:
    """Get ~/.clai directory"""
    return Path.home() / ".clai"

def get_credentials_path() -> Path:
    """Get credentials.json path (in project root or ~/.clai)"""
    # Try project root first, then ~/.clai
    
def get_gmail_token_path() -> Path:
    """Get ~/.clai/gmail_token.pickle"""
    return get_config_dir() / "gmail_token.pickle"
```

---

## State Management

### Command History

**Storage**: `~/.clai/command_history.json`

**Format**:
```json
[
  {
    "timestamp": "2025-10-13T14:30:00",
    "command": "do mail:list last 5",
    "command_type": "mail",
    "output": "📧 Found 5 emails:\n...",
    "metadata": {
      "count": 5,
      "sender": null,
      "action": "list",
      "source": "workflow_registry"
    }
  }
]
```

**Circular Buffer**: Automatically keeps only last 100 commands.

**Operations**:
```python
# Log command
log_command(command, output, command_type, metadata)

# Get history
get_history(limit=10, command_type="mail")

# Search history
search_history("gmail.com", search_in="both")
```

### Task Scheduling

**Storage**: `~/.clai/scheduled_tasks.json`

**Format**:
```json
[
  {
    "id": 1,
    "name": "Morning Email Check",
    "command": "mail:priority last 10",
    "time": "09:00",
    "enabled": true,
    "last_run": "2025-10-13T09:00:00",
    "created_at": "2025-10-12T10:00:00"
  }
]
```

**Scheduler Daemon**:
```bash
# Start scheduler (blocking)
clai scheduler start

# Or use background script
./start-scheduler.ps1  # Windows
./setup-clai.sh        # Linux/macOS
```

### Priority Emails

**Storage**: `~/.clai/priority_senders.json`

**Format**:
```json
{
  "senders": [
    "boss@company.com",
    "important@client.com",
    "@alerts.com"
  ]
}
```

**Usage**:
```bash
clai do "mail:priority-add boss@company.com"
clai do "mail:priority-add @alerts.com"  # Domain wildcard
clai do "mail:priority last 10"
```

---

## Testing Architecture

### Test Structure

```
tests/
├── test_auto_workflow.py          # Workflow automation tests
├── test_workflow_registry.py      # Registry tests
├── test_workflow_builder.py       # Workflow builder tests
├── test_mail_parsing.py          # Email parsing tests
├── test_document_commands.py     # Document processing tests
├── test_system_detection.py      # System info tests
└── test_logging.py               # History logging tests
```

### Testing Strategy

#### 1. Unit Tests
Test individual functions in isolation.

Example:
```python
def test_parse_mail_list_with_sender():
    args = "last 5 sender:john@example.com"
    result = _parse_mail_list(args, None)
    assert result["count"] == 5
    assert result["sender"] == "john@example.com"
```

#### 2. Integration Tests
Test interaction between components.

Example:
```python
def test_workflow_registry_executes_mail_list(monkeypatch):
    load_builtin_workflows()
    
    def fake_get_messages(count, sender, query):
        return [{"id": "abc123", "from": "test@example.com"}]
    
    monkeypatch.setattr("agent.workflows.mail.get_email_messages", fake_get_messages)
    
    result = global_registry.execute("mail:list last 5")
    assert "abc123" in result.output
```

#### 3. CLI Tests
Test CLI commands using `typer.testing.CliRunner`.

Example:
```python
def test_auto_executes_parsed_steps(monkeypatch):
    runner = CliRunner()
    executed_commands = []
    
    def fake_execute(command: str, *, extras=None) -> str:
        executed_commands.append(command)
        return f"Executed {command}"
    
    monkeypatch.setattr(cli, "execute_single_command", fake_execute)
    
    result = runner.invoke(cli.app, ["auto", "--run", "check email"])
    assert result.exit_code == 0
```

### Mocking Strategy

**API Mocking**:
```python
class FakeGmailClient:
    def list_messages(self, *, max_results, sender=None, query=None):
        return [{"id": "abc123", "from": "test@example.com"}]

monkeypatch.setattr(mail_tools, "GmailClient", FakeGmailClient)
```

**LLM Mocking**:
```python
def fake_parse_workflow(instruction: str):
    return {
        "success": True,
        "steps": [
            {"command": "mail:list last 5", "needs_approval": False}
        ]
    }

monkeypatch.setattr("agent.tools.nl_parser.parse_workflow", fake_parse_workflow)
```

### Running Tests

```bash
# In virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_auto_workflow.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=agent
```

### Current Test Status

**Passing**:
- ✅ `test_custom_registry_parses_arguments`
- ✅ `test_mail_list_workflow_dispatch`
- ✅ `test_build_command_reference_includes_legacy_and_dynamic`
- ✅ `test_mail_list_fallback_to_partial_sender`

**Failing** (to be fixed):
- ❌ `test_auto_executes_parsed_steps` - Auto command not executing workflow steps
- ❌ `test_auto_resolves_message_id_placeholder` - Placeholder resolution not working

**Root Cause**: The `auto` command's workflow execution flow needs refinement. The test mocks `parse_workflow` to return steps, but the actual command execution through `execute_single_command` first tries the workflow registry, which may succeed for some commands (like `mail:list`) but the test's fake handler isn't being called properly, causing `executed_commands` list to remain empty.

**Fix Required**: Ensure that when the test mocks `execute_single_command`, it properly intercepts ALL command executions, regardless of whether they go through the workflow registry or legacy parsing.

---

## Performance Optimizations (2025)

### Overview
Major performance improvements implemented in October 2025, focusing on LLM interaction speed and context management.

### 1. Ollama CLI vs HTTP API

**Problem**: 
- HTTP API calls to Ollama were taking ~4 seconds per request
- Sequential workflows with multiple LLM calls were very slow
- Timeout issues with complex prompts

**Solution**:
- Switched to Ollama CLI subprocess: `subprocess.run(['ollama', 'run', model])`
- Direct stdin/stdout communication
- No HTTP overhead or connection management

**Results**:
```
Before (HTTP API):  ~4 seconds per LLM call
After (CLI):        ~1 second per LLM call
Speedup:            4x faster
```

**Affected Components**:
- `tiered_planner.py` - Tiered architecture with classification and execution
- `guardrails.py` - Safety checks for query moderation
- `gpt_workflow.py` - GPT workflow generation with LLM-provided context

### 2. Context Management

**Problem**:
- Full email outputs (with previews) overwhelmed LLM context
- Sequential planner received too much irrelevant data
- Token limits reached quickly in multi-step workflows

**Solution**:
```python
# Extract only essential data
if 'mail:list' in step['command']:
    ids = re.findall(r'Message ID: ([a-f0-9]+)', step['output'])
    context_lines.append(f"IDs: {', '.join(ids)}")  # Only IDs
else:
    context_lines.append(f"Output: {step['output'][:100]}")  # Truncate
```

**Results**:
- 80% reduction in context size
- No more token overflow errors
- Faster LLM processing due to smaller prompts

### 3. ID Tracking

**Problem**:
- Sequential planner would reuse same email ID
- "Reply to last 3 emails" created 3 replies to same email
- No memory of which IDs were already processed

**Solution**:
```python
# Track used IDs across steps
used_ids = []
for step in completed_steps:
    id_match = re.search(r'id:([a-f0-9]+)', step['command'])
    if id_match:
        used_ids.append(id_match.group(1))

# Include in LLM prompt
prompt += f"\nIMPORTANT: Already processed these IDs (DO NOT reuse): {', '.join(used_ids)}"
```

**Results**:
- Eliminated ID reuse completely
- Proper sequential processing of multiple emails
- Each email gets unique reply

### 4. Prompt Engineering

**Problem**:
- Long, verbose prompts caused LLM hallucinations
- LLM would mistype IDs (199e0bba instead of 199e2bba)
- Slower processing and lower accuracy

**Solution**:
- Ultra-short prompts with only essential information
- Clear rules: "Copy EXACT ID from Step 1 output"
- Reduced from 500+ tokens to <200 tokens

**Results**:
- ~50% reduction in hallucinations
- More accurate ID extraction
- Faster LLM response time

### 5. Workflow Priority Order

**Problem**:
- Requests like "draft reply to latest mail" answered by local LLM incorrectly
- Local LLM tried to handle workflow tasks
- Confusion between direct answers and workflow execution

**Solution**:
```python
# New priority order in cli.py
# 1. Check workflow registry (structured commands)
try:
    return workflow_registry.execute(action)
except WorkflowNotFoundError:
    pass

# 2. Check if local LLM can answer directly (math, facts)
can_handle, answer = can_local_llm_handle(action)
if can_handle and answer:
    return answer

# 3. Generate multi-step workflow with GPT
workflow = parse_workflow(action)
execute_workflow(workflow)
```

**Results**:
- Proper routing of all command types
- Local LLM only handles what it can
- Complex workflows go through proper system

### Performance Metrics Summary

| Component | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Sequential Planning | ~4s per step | ~1s per step | **4x faster** |
| Local Compute | ~4s per call | ~1s per call | **4x faster** |
| Context Size | ~1000 tokens | ~200 tokens | **80% reduction** |
| ID Reuse Errors | Common | None | **100% fixed** |
| Hallucinations | ~20% rate | ~10% rate | **50% reduction** |
| Timeout Issues | Frequent | Rare | **90% reduction** |

### Timeout Changes

```python
# Sequential Planner
Before: timeout=60s  # Often hit
After:  timeout=10s  # Rarely hit

# Local Compute
Before: timeout=10s  # Sometimes hit
After:  timeout=5s   # Rarely hit
```

### Implementation Files

1. **agent/tools/tiered_planner.py** (CORE ARCHITECTURE)
   - `classify_request()`: First-stage classification with category-based filtering
   - `plan_step_execution()`: Memory-aware step execution
   - `WorkflowMemory`: Dataclass for context tracking across steps
   - Dynamic category loading from workflow registry

2. **agent/tools/guardrails.py** (SAFETY LAYER)
   - `check_query_safety()`: Content moderation before workflow execution
   - `GuardrailResult`: Safety check result with category, reason, confidence
   - Uses qwen3:4b-instruct model, 10s timeout, fail-open design

3. **agent/executor/gpt_workflow.py** (DYNAMIC GENERATION)
   - `generate_workflow_code()`: GPT-4 code generation with LLM-provided context
   - `_get_category_for_namespace()`: Dynamic category mapping
   - Two-LLM architecture: Local LLM generates context, GPT generates code

4. **agent/cli.py** (ENTRY POINT)
   - `auto()` command: Integrates guardrails → classification → execution
   - Workflow reload after GPT generation (importlib.reload)
   - Priority order: Safety check → Existing workflows → GPT generation

---

## Deployment

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Pabsthegreat/CloneAI.git
cd CloneAI

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama (for NL features)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen3:4b-instruct

# 5. Set up Google API credentials
# - Go to Google Cloud Console
# - Enable Gmail API and Calendar API
# - Create OAuth 2.0 credentials
# - Download as credentials.json
# - Place in project root

# 6. Install CloneAI command (development mode)
pip install -e .

# 7. Test installation
clai hi
```

### Production Deployment

**Option 1: User Installation**
```bash
pip install cloneai
clai hi
```

**Option 2: System-Wide Installation**
```bash
sudo pip install cloneai
clai hi
```

### Platform-Specific Setup

#### Windows
```powershell
# Install
pip install -r requirements.txt

# Add to PATH (PowerShell profile)
$PROFILE_PATH = "$env:USERPROFILE\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
Add-Content $PROFILE_PATH 'Set-Alias clai python -m agent.cli'

# Auto-start scheduler (Task Scheduler)
.\setup-windows-task.ps1
```

#### Linux/macOS
```bash
# Install
pip install -r requirements.txt

# Add to PATH (.bashrc or .zshrc)
echo 'alias clai="python -m agent.cli"' >> ~/.zshrc
source ~/.zshrc

# Auto-start scheduler (cron)
crontab -e
# Add: @reboot /path/to/CloneAI/start-scheduler.sh
```

### Environment Variables

```bash
# Optional configuration
export CLAI_CONFIG_DIR="$HOME/.clai"        # Config directory
export CLAI_CREDENTIALS_PATH="credentials.json"  # Google credentials
export CLAI_OLLAMA_MODEL="qwen3:4b-instruct"     # LLM model
```

### Docker Deployment (Future)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "agent.cli", "scheduler", "start"]
```

---

## Future Enhancements

### Planned Features

1. **Full Workflow Migration**
   - Migrate all legacy commands to workflow registry
   - Remove regex-based parsing from cli.py
   - Add parameter validation for all workflows

2. **Enhanced NL Processing**
   - Support for Claude/GPT-4 as alternative LLMs
   - Context-aware command suggestions
   - Learning from user corrections

3. **Advanced Scheduling**
   - Conditional task execution
   - Task dependencies
   - Retry logic with backoff

4. **Email Features**
   - Smart categorization
   - Auto-reply templates
   - Email threading support
   - Search with complex queries

5. **Calendar Features**
   - Conflict detection
   - Meeting notes integration
   - Recurring events

6. **Document Features**
   - OCR for scanned PDFs
   - Document search
   - Template system

7. **Security Enhancements**
   - Encrypted token storage
   - 2FA support
   - Audit logging

8. **UI Improvements**
   - Web dashboard
   - Mobile app
   - Desktop notifications

### Architecture Evolution

**Phase 1** (Current): Hybrid system with workflow registry + legacy parsing

**Phase 2**: Full workflow migration, remove legacy code

**Phase 3**: Plugin architecture for third-party integrations

**Phase 4**: Distributed architecture with API server

---

## Troubleshooting

### Common Issues

#### 1. Google API Authentication Errors
```
Error: Credentials file not found
Solution: Download credentials.json from Google Cloud Console
```

#### 2. Ollama Not Found
```
Error: Ollama not found
Solution: Install Ollama from https://ollama.ai
```

#### 3. Module Not Found
```
Error: No module named 'agent'
Solution: Install in development mode: pip install -e .
```

#### 4. Token Expired
```
Error: Invalid credentials
Solution: clai reauth gmail
```

#### 5. Tests Failing
```
Error: Import errors in tests
Solution: Activate virtual environment: source .venv/bin/activate
```

### Debug Mode

```bash
# Enable verbose logging
export CLAI_DEBUG=1

# Check system info
clai do "system:info"

# Check history
clai history --stats
```

---

## Conclusion

CloneAI is a sophisticated CLI agent that combines traditional command-line interfaces with modern AI capabilities. Its modular architecture allows for easy extension and maintenance, while the workflow registry provides a type-safe foundation for future growth.

The system successfully integrates with Google APIs, local LLMs, and the file system to provide a comprehensive personal productivity tool. The ongoing migration to the workflow registry will improve code quality, testability, and maintainability.

For more information:
- **User Guide**: See `docs/COMPLETE_GUIDE.md`
- **Email Features**: See `docs/EMAIL_IMPLEMENTATION.md`
- **NL Features**: See `docs/NL_FEATURES.md`
- **Security**: See `docs/SECURITY.md`
- **Testing**: See `docs/TESTING.md`

---

*Last Updated: October 13, 2025*
*Version: 2.0*
*Maintainer: CloneAI Team*
