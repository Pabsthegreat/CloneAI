from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from agent.skills.mail.client import GmailClient
from typing import Dict, Any
import json

@register_workflow(
    namespace="mail",
    name="list",
    summary="Auto-generated workflow for `mail:list`",
    description="Implements the CLI command `mail:list`.",
    parameters=(),
    metadata={
        "category": "MAIL COMMANDS",
        "usage": "mail:list",
        "examples": ["Example: mail:list"],
    }
)
def mail_list_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    client = GmailClient()  # Automatically handles OAuth tokens
    try:
        emails = client.list_messages(max_results=5)
        if not emails:
            return "No emails found."
        email_metadata = [
            {
                "id": email['id'],
                "from": email['from'],
                "subject": email['subject'],
                "date": email['date']
            }
            for email in emails
        ]
        return json.dumps(email_metadata)
    except Exception as e:
        return f"Error retrieving emails: {str(e)}"
