"""
Natural Language Command Parser using Ollama (Qwen3:4b-instruct)

This module translates natural language instructions into CloneAI commands.
"""

import datetime
import json
import os
from typing import Dict, List, Optional

from agent.config.runtime import LOCAL_PLANNER
from agent.core.llm.ollama import run_ollama
from agent.workflows import build_command_reference

# Command documentation for the LLM (generated from the workflow registry plus legacy commands)
COMMAND_REFERENCE = build_command_reference()


def refresh_command_reference() -> str:
    """Regenerate the command reference after workflows are added."""
    global COMMAND_REFERENCE
    try:
        build_command_reference.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:
        pass
    COMMAND_REFERENCE = build_command_reference()
    return COMMAND_REFERENCE

def get_user_context() -> str:
    """
    Build user context information for the LLM.
    Returns context about current directory, user info, etc.
    """
    cwd = os.getcwd()
    
    # Try to get user info from environment or config
    home_dir = os.path.expanduser("~")
    username = os.environ.get("USER") or os.environ.get("USERNAME") or "User"
    
    # Check if there's a .clai config with user info
    user_info = {
        "name": username,
        "email": None,
        "srn": "PES1UG23CS022",  # Default SRN, can be customized
    }
    
    config_path = os.path.join(home_dir, ".clai", "user_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
                user_info.update(saved_config)
        except:
            pass
    
    context = f"""CURRENT CONTEXT:
- Working Directory: {cwd}
- User: {user_info['name']}
- SRN/ID: {user_info['srn']}"""
    
    if user_info.get('email'):
        context += f"\n- Email: {user_info['email']}"
    
    context += f"""

IMPORTANT PATH RULES:
- When user mentions files in "this folder", "current folder", "cloneai folder", use the working directory: {cwd}
- For files mentioned without path, assume they are in: {cwd}
- Example: "file.pdf" should be referenced as just "file.pdf" (not "cloneai/file.pdf")
- Use relative paths from current directory: {cwd}

USER PERSONALIZATION:
- When user says "my SRN" or "my ID", use: {user_info['srn']}
- When user says "send from me" or "my email", the system will use authenticated Gmail account
"""
    
    return context

def call_ollama(prompt: str, model: str = "qwen3:4b-instruct") -> Optional[str]:
    """
    Call the local Ollama CLI to get an LLM response using deterministic settings.
    
    Args:
        prompt: The prompt to send to the model
        model: Ollama model name (default: qwen3:4b-instruct)
        
    Returns:
        Model response text or None if error
    """
    return run_ollama(
        prompt,
        profile=LOCAL_PLANNER,
        model=model,
        timeout=60,
    )

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
            "mail:list from user@example.com"
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
    
    user_context = get_user_context()

    prompt = f"""You are an instruction generator, who converts natural language requests into exact atomic CloneAI commands.

{user_context}

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
2. Use exact command syntax from the reference.
3. Create the most specific and simple command possible for each step in workflow.
4. If you need information (like message ID), mention it in explanation
5. For dates, use ISO format and 24hr format for time(YYYY-MM-DDTHH:MM:SS)
6. Today's date is {datetime.date.today()}.
7. For subject/title/body text with spaces, keep them as-is (spaces are OK)


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
    
    user_context = get_user_context()

    prompt = f"""You are a workflow parser, instruction generator for CloneAI. Break down multi-step tasks into a sequence of atomic simple CloneAI commands.

{user_context}

{COMMAND_REFERENCE}

User workflow: "{instruction}"

IMPORTANT: First determine if this is an ACTION or a QUESTION:
- ACTION: Tasks that require executing commands or following a workflow(send email, schedule meeting, list emails, etc.)
- QUESTION: General knowledge queries, definitions, information requests (what is X?, who is Y?, define Z)

For QUESTIONS that don't need a workflow and you can handle it answer directly, do not overestimate your capabilities here, if you cannot answer it go for generating a workflow.
- Return empty steps array: {{"steps": [], "reasoning": "This is a general knowledge question, not a workflow task"}}

For ACTIONS (tasks that require executing commands or following a workflow):

Rules:
1. ONE atomic action per step - each step executes ONE command.
2. needs_approval=true for send/delete/modify operations, false for read-only.
3. ALWAYS check the COMMAND REFERENCE above for available commands before creating steps.
4. Use the MOST SPECIFIC command available (e.g., mail:summarize for summarization, not mail:view).
5. For workflows needing data from previous steps, use placeholders like MESSAGE_ID or DRAFT_ID.
6. Create an atomic step-by-step execution plan. Respond with ONLY valid JSON:
{{
  "steps": [
    {{
      "command": "command to execute",
      "description": "what this step does",
      "needs_approval": true/false
    }}
  ],
}}

Key workflow patterns:
- To summarize an email: mail:list → mail:summarize id:MESSAGE_ID
- To reply to an email: mail:list → mail:reply id:MESSAGE_ID
- To draft new email: mail:draft (body is optional, AI generates if missing)
- To view email content: mail:list → mail:view id:MESSAGE_ID

IMPORTANT - Distinguish between QUESTIONS and ACTIONS:
QUESTIONS (return empty steps): General knowledge queries like "what is X?", "who is Y?", "define Z"
ACTIONS (create workflow steps): Tasks requiring command execution like "send email", "list emails", "summarize email"

JSON only:"""

    # Debug logging controlled by env var
    if os.getenv("CLAI_DEBUG") == "1":
        print(f"[NL_PARSER] Prompt length: {len(prompt)} chars")
    
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
    
    # Get system context (working directory, user info)
    system_context = get_user_context()
    
    prompt = f"""You are an email composition assistant. Generate a professional email based on the user's instruction.

{system_context}

User instruction: "{instruction}"
{f"Additional Context: {user_context}" if user_context else ""}

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
