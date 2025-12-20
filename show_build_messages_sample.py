#!/usr/bin/env python3
"""
Sample script to show what _build_messages() produces without calling the OpenAI API.
Run: python show_build_messages_sample.py
"""

import sys
import os
from dataclasses import dataclass
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.executor.gpt_workflow import GPTWorkflowGenerator, WorkflowGenerationContext
from agent.executor.workflow_builder import WorkflowRecipe


def main():
    # Create a realistic sample recipe
    recipe = WorkflowRecipe(
        namespace="mail",
        name="search",
        summary="Search emails by subject or content",
        description="Search through Gmail using keywords and filters to find specific emails.",
    )

    # Create a realistic sample context
    context = WorkflowGenerationContext(
        command_reference="""
Available commands:
- mail:list [last N] [sender:EMAIL] [category:CATEGORY] - List recent emails
- mail:view id:MESSAGE_ID - View full email content
- mail:reply id:MESSAGE_ID [to:EMAIL] - Create draft reply
- mail:send to:EMAIL subject:SUBJECT body:BODY - Send email
- calendar:list [next N] - List upcoming calendar events
- calendar:create summary:TITLE time:DATETIME - Create calendar event
        """.strip(),
        
        project_tree="""
CloneAI/
├── agent/
│   ├── cli.py (2352 lines) - Main CLI router
│   ├── workflows/
│   │   ├── __init__.py - Workflow exports
│   │   ├── registry.py - Registration engine
│   │   ├── mail.py - Mail workflow handlers
│   │   └── generated/ - Auto-generated workflows
│   ├── tools/
│   │   ├── mail.py (1151 lines) - Gmail integration
│   │   ├── calendar.py - Google Calendar
│   │   ├── nl_parser.py - Natural language parser
│   │   └── sequential_planner.py - Multi-step planning
│   └── executor/
│       ├── workflow_builder.py - Workflow builder
│       └── gpt_workflow.py - This generator
├── tests/ - Test suite
└── docs/ - Documentation
        """.strip(),
        
        registry_source="""
from dataclasses import dataclass
from typing import Any, Callable, Dict, Sequence

@dataclass
class ParameterSpec:
    name: str
    description: str = ""
    type: Callable[[str], Any] = str
    required: bool = False
    default: Any = None
    aliases: Sequence[str] = ()

@dataclass
class WorkflowContext:
    command: str
    user_id: str = "default"
    extras: Dict[str, Any] = field(default_factory=dict)

def register_workflow(
    namespace: str,
    name: str,
    summary: str,
    description: str = "",
    parameters: Sequence[ParameterSpec] = (),
    metadata: Dict[str, Any] = None,
):
    '''Decorator to register a workflow handler.'''
    def decorator(handler):
        # Registration logic here
        return handler
    return decorator
        """.strip(),
        
        sample_workflows={
            "agent/workflows/mail.py": """
from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from agent.skills.mail.client import list_emails, get_full_email
from typing import Dict, Any

@register_workflow(
    namespace="mail",
    name="list",
    summary="List recent emails from Gmail",
    description="Retrieve and display recent emails with optional filters.",
    parameters=(
        ParameterSpec(
            name="count",
            description="Number of emails to retrieve",
            type=int,
            required=False,
            default=5,
        ),
        ParameterSpec(
            name="sender",
            description="Filter by sender email address",
            type=str,
            required=False,
            default=None,
        ),
        ParameterSpec(
            name="category",
            description="Gmail category (promotions, social, updates, primary)",
            type=str,
            required=False,
            default=None,
        ),
    ),
    metadata={
        "usage": "mail:list [last COUNT] [sender:EMAIL] [in CATEGORY]",
        "examples": [
            "mail:list last 10",
            "mail:list sender:boss@company.com",
            "mail:list last 5 in promotions",
        ],
    },
)
def mail_list_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    count = params.get("count", 5)
    sender = params.get("sender")
    category = params.get("category")
    
    try:
        result = list_emails(count=count, sender=sender, category=category)
        return result
    except Exception as e:
        return f"❌ Error listing emails: {str(e)}"
            """.strip(),
        },
        
        tool_summaries={
            "agent/tools/mail.py": """
# Gmail API integration module

class GmailClient:
    '''Wrapper for Gmail API operations with OAuth authentication.'''
    
    def list_messages(self, max_results: int, sender: str = None, query: str = None):
        '''List messages from Gmail inbox.
        
        Query examples:
        - "in:inbox" - Inbox only (default)
        - "category:promotions" - Promotions category
        - "from:sender@example.com" - From specific sender
        '''
        pass
    
    def get_message(self, message_id: str):
        '''Get full message details by ID.'''
        pass
    
    def search_messages(self, query: str, max_results: int = 10):
        '''Search Gmail using query syntax.
        
        Query operators:
        - subject:text - Search in subject
        - from:email - From sender
        - to:email - To recipient
        - has:attachment - Has attachments
        - after:YYYY/MM/DD - After date
        - before:YYYY/MM/DD - Before date
        '''
        pass

def list_emails(count: int = 5, sender: str = None, query: str = None, category: str = None) -> str:
    '''List emails with optional filters. Returns formatted string.'''
    pass

def get_full_email(message_id: str) -> str:
    '''Get full email content by ID. Returns formatted string.'''
    pass

def create_draft_email(to: str, subject: str, body: str) -> str:
    '''Create draft email in Gmail. Returns draft ID.'''
    pass
            """.strip(),
        },
        
        existing_workflows=["mail:list", "mail:view", "mail:reply", "mail:draft", "calendar:list", "calendar:create"],
    )

    # Create generator and build messages
    generator = GPTWorkflowGenerator(model="gpt-4.1", api_key="fake-key-not-used")
    
    print("=" * 80)
    print("BUILD MESSAGES OUTPUT SAMPLE")
    print("=" * 80)
    print()
    print("Recipe:")
    print(f"  Command: {recipe.command_key()}")
    print(f"  Namespace: {recipe.namespace}")
    print(f"  Name: {recipe.name}")
    print(f"  Summary: {recipe.summary}")
    print()
    print("=" * 80)
    print()
    
    # Call _build_messages (no API call)
    messages = generator._build_messages(recipe, context, previous_errors=[])
    
    # Display the messages
    for i, message in enumerate(messages, 1):
        role = message["role"]
        content = message["content"]
        
        print(f"MESSAGE {i}/{len(messages)}")
        print(f"Role: {role}")
        print("-" * 80)
        print(content)
        print()
        print("=" * 80)
        print()
    
    # Summary
    print("\nSUMMARY:")
    print(f"  Total messages: {len(messages)}")
    print(f"  System prompt length: {len(messages[0]['content'])} chars")
    print(f"  User prompt length: {len(messages[1]['content'])} chars")
    print(f"  Total prompt length: {sum(len(str(m['content'])) for m in messages)} chars")
    print()
    print("NOTE: This is what would be sent to GPT-4.1 (but we didn't call the API).")
    print()


if __name__ == "__main__":
    main()
