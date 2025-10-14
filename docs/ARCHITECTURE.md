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

CloneAI is a personal CLI agent built with Python that provides an intelligent command-line interface for managing emails, calendars, documents, and automated tasks. It combines traditional command parsing with AI-powered natural language processing using local LLMs (via Ollama).

### Key Features
- **Email Management**: Gmail integration for reading, drafting, sending emails
- **Calendar Management**: Google Calendar integration for events and meetings
- **Document Processing**: PDF/DOCX/PPT conversion and merging
- **Task Scheduling**: Automated task execution at specified times
- **Natural Language Processing**: Convert plain English to CLI commands
- **Workflow Automation**: Multi-step command execution
- **Command History**: Persistent logging of all commands and outputs

### Technology Stack
- **Language**: Python 3.9+
- **CLI Framework**: Typer (built on top of Click)
- **APIs**: Google Gmail API, Google Calendar API
- **LLM Integration**: Ollama (local LLM server)
- **Document Processing**: PyPDF2, python-docx, python-pptx, pdf2docx
- **Task Scheduling**: schedule library
- **State Management**: JSON-based persistence

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
│   │   ├── documents.py       # Document processing
│   │   ├── scheduler.py       # Task scheduling
│   │   ├── nl_parser.py       # Natural language parser (Ollama)
│   │   ├── email_parser.py    # Email parsing utilities
│   │   └── priority_emails.py # Priority email management
│   │
│   └── workflows/             # New workflow system
│       ├── __init__.py        # Workflow exports & loading
│       ├── registry.py        # Workflow registration engine
│       ├── catalog.py         # Legacy command catalog
│       └── mail.py            # Mail workflow handlers
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

**Example**:
```python
@app.command()
def do(action: str):
    """Execute a command"""
    # 1. Try workflow registry (new system)
    try:
        result = workflow_registry.execute(action, extras=registry_extras)
        return result.output
    except WorkflowNotFoundError:
        pass  # Fall through to legacy
    
    # 2. Try legacy command parsing
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
def get_email_messages(count: int, sender: str, query: str) -> List[Dict]:
    """
    Retrieves emails from Gmail with optional filters.
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
