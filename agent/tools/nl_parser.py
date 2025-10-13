"""
Natural Language Command Parser using Ollama (Qwen3:4b-instruct)

This module translates natural language instructions into CloneAI commands.
"""

import json
import subprocess
import sys
from typing import Dict, Optional, List
import datetime
import os


# Command documentation for the LLM
COMMAND_REFERENCE = """
CloneAI Command Reference:
==========================

EMAIL COMMANDS:
- mail:list [last N] [from EMAIL]           # List emails (default: last 5)
- mail:view id:MESSAGE_ID                   # View full email content
- mail:download id:MESSAGE_ID [dir:PATH]    # Download email attachments
- mail:draft to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL]  # Create draft
- mail:send to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL] [attachments:PATHS]  # Send email
- mail:send draft-id:DRAFT_ID               # Send existing draft
- mail:drafts [last N]                      # List draft emails
- mail:priority [last N]                    # List priority emails
- mail:priority-add EMAIL|@DOMAIN           # Add priority sender
- mail:priority-remove EMAIL|@DOMAIN        # Remove priority sender
- mail:priority-list                        # Show priority configuration
- mail:scan-meetings [hours:N]              # Scan for meeting invitations
- mail:add-meeting email-id:MSG_ID [time:DATETIME]  # Add meeting to calendar
- mail:invite to:EMAIL subject:TEXT time:DATETIME duration:MINS [platform:TEXT]  # Send meeting invite

CALENDAR COMMANDS:
- calendar:create title:TEXT start:DATETIME [end:DATETIME|duration:MINS] [location:TEXT] [description:TEXT]
- calendar:list [next N]                    # List upcoming events (default: next 10)

SCHEDULER COMMANDS:
- tasks                                     # List all scheduled tasks
- task:add name:TEXT command:COMMAND time:HH:MM  # Add scheduled task
- task:remove TASK_ID                       # Remove task by ID
- task:toggle TASK_ID                       # Enable/disable task

DOCUMENT COMMANDS:
- merge pdf                                 # Merge PDF files (interactive)
- merge ppt                                 # Merge PowerPoint files (interactive)
- convert pdf-to-docx                       # Convert PDF to Word (interactive)
- convert docx-to-pdf                       # Convert Word to PDF (interactive, Windows only)
- convert ppt-to-pdf                        # Convert PPT to PDF (interactive, Windows only)

CASCADING COMMANDS:
- COMMAND1 && COMMAND2 && COMMAND3          # Chain multiple commands

Examples:
- "show me my last 10 emails" → mail:list last 10
- "list emails from john@example.com" → mail:list from john@example.com
- "download attachments from message 199abc123" → mail:download id:199abc123
- "create a meeting called Team Sync on Oct 15 at 2pm for 1 hour" → calendar:create title:Team Sync start:2025-10-15T14:00:00 duration:60
- "show my next 5 calendar events" → calendar:list next 5
- "send email to bob@test.com with subject Hello and body Hi there" → mail:send to:bob@test.com subject:Hello body:Hi there

IMPORTANT NOTES:
- Message IDs are hexadecimal strings (e.g., 199abc123def)
- Datetime format: YYYY-MM-DDTHH:MM:SS (e.g., 2025-10-15T14:00:00)
- Time format for tasks: HH:MM (24-hour, e.g., 09:00, 14:30)
- Duration in minutes (e.g., 60 for 1 hour, 30 for 30 minutes)
- Multiple attachments: comma-separated paths (no spaces)
- If user says "last 5 emails", use "mail:list last 5"
- If user mentions downloading attachments, they need to provide the message ID

CRITICAL MEETING RULES:
- If user mentions scheduling/creating a meeting WITH another person's EMAIL → use mail:invite (sends email invitation)
- If user only wants to add to their OWN calendar (no email mentioned) → use calendar:create
- mail:invite REQUIRES: to:EMAIL, subject:TOPIC, time:DATETIME, duration:MINS
- Example: "schedule meeting with john@test.com" → mail:invite to:john@test.com ...
- Example: "add to my calendar" → calendar:create ...
"""


def call_ollama(prompt: str, model: str = "qwen3:4b-instruct") -> Optional[str]:
    """
    Call Ollama API to get LLM response.
    
    Args:
        prompt: The prompt to send to the model
        model: Ollama model name (default: qwen3:4b-instruct)
        
    Returns:
        Model response text or None if error
    """
    try:
        # Use ollama CLI with piped input
        process = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send prompt and get response
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


def parse_natural_language(user_input: str, model: str = "qwen3:4b-instruct") -> Dict[str, any]:
    """
    Parse natural language input into a CloneAI command.
    
    Args:
        user_input: Natural language instruction from user
        model: Ollama model to use (default: qwen3:4b-instruct)
        
    Returns:
        Dictionary with:
        - command: The parsed CloneAI command string
        - confidence: Confidence level (high/medium/low)
        - explanation: Brief explanation of the parsing
        - success: Boolean indicating if parsing was successful
    """
    
    prompt = f"""You are a command parser for CloneAI, a CLI tool. Convert the user's natural language request into the exact CloneAI command syntax.

{COMMAND_REFERENCE}

User request: "{user_input}"

Analyze the request and respond with ONLY a valid JSON object (no markdown, no extra text):
{{
  "command": "the exact CloneAI command",
  "confidence": "high|medium|low",
  "explanation": "brief explanation of what this command does"
}}

Rules:
1. Output ONLY valid JSON, nothing else
2. Use exact command syntax from the reference
3. If the request is ambiguous, make reasonable assumptions
4. If you need information (like message ID), mention it in explanation
5. For dates, use ISO format (YYYY-MM-DDTHH:MM:SS)
6. For "today" use current date {sys.current_date}, "tomorrow" is {sys.current_date + datetime.timedelta(days=1)}
7. For subject/title/body text with spaces, keep them as-is (spaces are OK)
8. Use 24-hour time format (1:30 PM = 13:30, 2:00 PM = 14:00)

Respond with JSON only:"""

    # Call Ollama
    response = call_ollama(prompt, model)
    
    if not response:
        return {
            "success": False,
            "command": None,
            "confidence": "low",
            "explanation": "Failed to get response from Ollama"
        }
    
    # Parse JSON response
    try:
        # Try to extract JSON from response (in case model adds extra text)
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
        
        parsed = json.loads(response)
        
        return {
            "success": True,
            "command": parsed.get("command", ""),
            "confidence": parsed.get("confidence", "medium"),
            "explanation": parsed.get("explanation", "")
        }
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse LLM response as JSON: {e}")
        print(f"Raw response: {response}")
        return {
            "success": False,
            "command": None,
            "confidence": "low",
            "explanation": f"Could not parse LLM response: {str(e)}"
        }


def get_command_suggestions(user_input: str) -> List[str]:
    """
    Get command suggestions based on partial user input.
    
    Args:
        user_input: Partial user input
        
    Returns:
        List of suggested commands
    """
    suggestions = []
    lower_input = user_input.lower()
    
    # Email suggestions
    if any(word in lower_input for word in ["email", "mail", "inbox", "message"]):
        suggestions.extend([
            "mail:list last 10",
            "mail:list from user@example.com",
            "mail:priority"
        ])
    
    # Calendar suggestions
    if any(word in lower_input for word in ["calendar", "meeting", "event", "schedule"]):
        suggestions.extend([
            "calendar:list next 5",
            "calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60"
        ])
    
    # Download suggestions
    if any(word in lower_input for word in ["download", "attachment"]):
        suggestions.append("mail:download id:MESSAGE_ID")
    
    return suggestions[:5]  # Return top 5 suggestions


def parse_workflow(instruction: str, model: str = "qwen3:4b-instruct") -> Dict[str, any]:
    """
    Parse multi-step workflow instructions into a sequence of CloneAI commands.
    
    Args:
        instruction: Natural language workflow description
                    e.g., "check my last 5 emails and reply to each one"
        model: Ollama model to use
        
    Returns:
        Dictionary with:
        - steps: List of command steps to execute
        - requires_approval: Whether to ask for approval between steps
        - success: Boolean indicating if parsing was successful
    """
    
    prompt = f"""You are a workflow parser for CloneAI. Break down multi-step tasks into a sequence of CloneAI commands.

{COMMAND_REFERENCE}

User workflow: "{instruction}"

Analyze the workflow and create a step-by-step execution plan. Respond with ONLY valid JSON:
{{
  "steps": [
    {{
      "command": "command to execute",
      "description": "what this step does",
      "needs_approval": true/false
    }}
  ],
  "reasoning": "brief explanation of the workflow"
}}

WORKFLOW RULES:
1. Break complex tasks into atomic commands
2. For "check emails and reply", list emails first, then generate replies for each
3. Set needs_approval=true for actions that send/delete/modify data
4. Set needs_approval=false for read-only operations (list, view, etc.)
5. For "reply to emails", add individual reply steps for each email

Examples:
- "check last 5 emails and reply to them" → 
  Step 1: mail:list last 5
  Step 2: (for each email) generate reply and send

Respond with JSON only:"""

    response = call_ollama(prompt, model)
    
    if not response:
        return {
            "success": False,
            "steps": [],
            "reasoning": "Failed to get response from Ollama"
        }
    
    try:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            if response.startswith("json"):
                response = response[4:].strip()
        
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            response = response[start:end]
        
        parsed = json.loads(response)
        
        return {
            "success": True,
            "steps": parsed.get("steps", []),
            "reasoning": parsed.get("reasoning", "")
        }
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse workflow: {e}")
        print(f"Raw response: {response}")
        return {
            "success": False,
            "steps": [],
            "reasoning": f"Could not parse response: {str(e)}"
        }


def generate_email_content(instruction: str, user_context: str = "", model: str = "qwen3:4b-instruct") -> Dict[str, any]:
    """
    Generate email content (subject + body) from natural language instruction.
    
    Args:
        instruction: Natural language description of what email to send
                    e.g., "send an email to John about the project deadline"
        user_context: Optional context about the user/situation
        model: Ollama model to use
        
    Returns:
        Dictionary with:
        - to: Recipient email address (if mentioned)
        - subject: Generated email subject
        - body: Generated email body
        - success: Boolean indicating if generation was successful
    """
    
    prompt = f"""You are an email composition assistant. Generate a professional email based on the user's instruction.

User instruction: "{instruction}"
{f"Context: {user_context}" if user_context else ""}

Generate a professional, clear, and appropriately formal email. Respond with ONLY a valid JSON object (no markdown, no extra text):
{{
  "to": "recipient@example.com",
  "subject": "Clear and concise subject line",
  "body": "Professional email body with proper greeting, content, and closing.\\n\\nUse \\\\n for line breaks."
}}

Rules:
1. Output ONLY valid JSON, nothing else
2. Extract recipient email from instruction if mentioned (use "to" field), otherwise leave as "RECIPIENT_EMAIL"
3. Create a clear, specific subject line (3-10 words)
4. Body should include:
   - Appropriate greeting (Dear [Name]/Hi [Name]/Hello,)
   - Clear main message
   - Closing (Best regards/Thanks/Sincerely)
   - Signature placeholder if appropriate
5. Keep professional yet friendly tone
6. Use \\n for line breaks in the body
7. If instruction mentions specific details, include them
8. If unclear, make reasonable professional assumptions

Respond with JSON only:"""

    response = call_ollama(prompt, model)
    
    if not response:
        return {
            "success": False,
            "to": None,
            "subject": None,
            "body": None,
            "error": "Failed to get response from Ollama"
        }
    
    # Parse JSON response
    try:
        # Clean response
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
        
        parsed = json.loads(response)
        
        # Decode escaped newlines in the body
        body = parsed.get("body", "")
        # Replace literal \n with actual newlines
        body = body.replace("\\n", "\n")
        
        return {
            "success": True,
            "to": parsed.get("to", "RECIPIENT_EMAIL"),
            "subject": parsed.get("subject", ""),
            "body": body
        }
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse email generation response: {e}")
        print(f"Raw response: {response}")
        return {
            "success": False,
            "to": None,
            "subject": None,
            "body": None,
            "error": f"Could not parse LLM response: {str(e)}"
        }


if __name__ == "__main__":
    # Test the parser
    test_inputs = [
        "show me my last 10 emails",
        "list emails from john@example.com",
        "create a meeting tomorrow at 2pm",
        "download attachments from message abc123"
    ]
    
    print("🧪 Testing Natural Language Parser\n")
    for test in test_inputs:
        print(f"Input: {test}")
        result = parse_natural_language(test)
        print(f"✓ Command: {result['command']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Explanation: {result['explanation']}\n")
