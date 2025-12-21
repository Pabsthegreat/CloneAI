"""
Integration with the OpenAI Responses API for generating new workflow modules.
"""

from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - library may not be installed during tests
    OpenAI = None  # type: ignore

from agent.config.runtime import (
    REMOTE_GENERATOR_MAX_TOKENS,
    REMOTE_GENERATOR_MODEL,
    REMOTE_GENERATOR_TEMPERATURE,
)
from agent.executor.workflow_builder import WorkflowRecipe


class GPTWorkflowError(Exception):
    """Raised when GPT-based workflow generation fails."""


@dataclass
class GeneratedArtifact:
    """Represents a generated file (module or test)."""

    path: str
    content: str
    description: Optional[str] = None


@dataclass
class WorkflowGenerationContext:
    """Context provided to GPT for workflow generation."""

    command_reference: str
    project_tree: str
    registry_source: str
    sample_workflows: Dict[str, str]
    tool_summaries: Dict[str, str]
    existing_workflows: List[str]


@dataclass
class GPTWorkflowResult:
    """Parsed result from the GPT generator."""

    module_code: str
    tests: List[GeneratedArtifact] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    summary: str = ""


class GPTWorkflowGenerator:
    """Wrapper around the OpenAI responses API to produce new workflow implementations."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("CLAI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or REMOTE_GENERATOR_MODEL
        self.temperature = temperature if temperature is not None else REMOTE_GENERATOR_TEMPERATURE
        self.max_output_tokens = max_output_tokens if max_output_tokens is not None else REMOTE_GENERATOR_MAX_TOKENS

    def is_configured(self) -> bool:
        """Return True if the OpenAI client can be initialised."""
        return bool(self.api_key and OpenAI is not None)

    def generate(
    self,
    recipe: WorkflowRecipe,
    context: WorkflowGenerationContext,
    *,
    previous_errors: Optional[List[str]] = None,
    ) -> GPTWorkflowResult:
        if not self.is_configured():
            raise GPTWorkflowError("OpenAI API is not configured or openai library not installed.")

        client = OpenAI(api_key=self.api_key)  # type: ignore[call-arg]
        messages = self._build_messages(recipe, context, previous_errors or [])

        # Join system+user into a single text input for Responses API.
        # (We keep roles inside the text for clarity.)
        input_text = "\n\n".join(
            str(m["content"]) for m in messages if isinstance(m.get("content"), str)
        )

        # Optional: hard size cap (simple guard)
        def _truncate(s: str, max_chars: int = 110_000) -> str:
            return s if len(s) <= max_chars else s[:max_chars] + "\n\n[TRUNCATED]\n"

        input_text = _truncate(input_text)

        try:
            # Use chat completions API (OpenAI 2.x)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior Python engineer generating production-ready workflow modules. Output must be valid JSON matching the required schema."},
                    {"role": "user", "content": input_text}
                ],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Extract and display token usage information
            if resp.usage:
                input_tokens = resp.usage.prompt_tokens
                output_tokens = resp.usage.completion_tokens
                total_tokens = resp.usage.total_tokens
                
                print(f"\n{'='*60}")
                print(f"🤖 GPT Workflow Generation - Token Usage")
                print(f"{'='*60}")
                print(f"Command: {recipe.command_key()}")
                print(f"Model: {self.model}")
                print(f"Input Tokens:  {input_tokens:,}")
                print(f"Output Tokens: {output_tokens:,}")
                print(f"Total Tokens:  {total_tokens:,}")
                print(f"{'='*60}\n")
            else:
                print(f"⚠️  Token usage information not available in response")
                
        except Exception as exc:  # pragma: no cover
            raise GPTWorkflowError(f"OpenAI API request failed: {exc}") from exc

        # Extract response text from chat completion
        response_text = resp.choices[0].message.content if resp.choices else None

        if not response_text:
            raise GPTWorkflowError("OpenAI API returned an empty response.")

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            # Helpful context in the error for debugging
            snippet = response_text[:800]
            raise GPTWorkflowError(f"OpenAI response was not valid JSON: {exc}\nRaw (head): {snippet}") from exc

        module_code = payload.get("module_code", "")
        if not module_code:
            raise GPTWorkflowError("OpenAI response missing 'module_code'.")

        tests_payload = payload.get("tests", []) or []
        tests: List[GeneratedArtifact] = []
        for test in tests_payload:
            if isinstance(test, dict):
                path = test.get("path")
                content = test.get("content")
                if path and content:
                    tests.append(GeneratedArtifact(path=path, content=content, description=test.get("description")))

        notes = payload.get("notes", []) or []
        if not isinstance(notes, list):
            notes = [str(notes)]
        summary = payload.get("summary", "")

        return GPTWorkflowResult(module_code=module_code, tests=tests, notes=notes, summary=summary)

    def _get_category_for_namespace(
        self, 
        namespace: str, 
        context: WorkflowGenerationContext
    ) -> str:
        """
        Dynamically determine the category for a namespace by looking at existing workflows.
        
        This avoids hardcoding category mappings and allows the system to learn from
        existing workflows in the registry.
        """
        # Check existing workflows in this namespace to find their category
        from agent.workflows import registry as workflow_registry
        
        specs = workflow_registry.list(namespace=namespace)
        if specs:
            # Use the category from the first workflow in this namespace
            for spec in specs:
                if spec.metadata and "category" in spec.metadata:
                    return spec.metadata["category"]
        
        # Fallback: Create a category name from the namespace
        # Convert namespace to a readable category name
        namespace_to_category = {
            "mail": "MAIL COMMANDS",
            "calendar": "CALENDAR COMMANDS", 
            "task": "SCHEDULER COMMANDS",
            "tasks": "SCHEDULER COMMANDS",
            "doc": "DOCUMENT COMMANDS",
            "convert": "DOCUMENT COMMANDS",
            "image": "IMAGE COMMANDS",
            "merge": "DOCUMENT COMMANDS",
            "system": "GENERAL COMMANDS",
            "web": "WEB COMMANDS",
            "web_search": "WEB COMMANDS",
            "math": "MATH COMMANDS",
            "text": "TEXT COMMANDS",
        }
        
        return namespace_to_category.get(namespace, f"{namespace.upper()} COMMANDS")

    def _build_messages(
        self,
        recipe: WorkflowRecipe,
        context: WorkflowGenerationContext,
        previous_errors: List[str],
    ) -> List[Dict[str, object]]:
        """Construct system/user prompts for the GPT call."""
        command_key = recipe.command_key()
        namespace = recipe.namespace
        module_path = f"agent/workflows/generated/{namespace}_{recipe.name}.py"

        # Take only the FIRST sample workflow (most relevant)
        sample_workflow = ""
        if context.sample_workflows:
            first_path = next(iter(context.sample_workflows))
            first_code = context.sample_workflows[first_path]
            # Truncate to ~600 chars for brevity
            truncated = first_code[:600] + "\n    # ... (truncated)" if len(first_code) > 600 else first_code
            sample_workflow = f"# Reference: {first_path}\n{textwrap.indent(truncated.strip(), '    ')}"

        # Extract only key function signatures from tools (not full implementations)
        tool_hints = []
        for path, code in context.tool_summaries.items():
            # Extract just function definitions (first 300 chars usually contains key signatures)
            lines = code[:300].split('\n')
            # Keep lines with 'def ' or class names
            key_lines = [l.strip() for l in lines if 'def ' in l or 'class ' in l][:3]
            if key_lines:
                tool_hints.append(f"{path}: {', '.join(key_lines[:2])}")
        
        # Add common tool import mappings to help GPT use correct paths
        tool_imports = """
IMPORTANT - Correct import paths for common tools:
  - Web search: from agent.tools.web_search import search_web_formatted, WebSearchTool
  - Documents: from agent.tools.documents import DocumentManager
  - LLM/AI: from agent.core.llm.ollama import run_ollama
  - NL Parser: from agent.tools.nl_parser import parse_natural_language, call_ollama
  - Image Generation: from agent.tools.image_generation import generate_image
  - Do not create workflows specific a single file. 

⚠️  CRITICAL - ALWAYS INCLUDE ALL NECESSARY IMPORTS:
  - Standard library: json, os, pathlib, datetime, typing, subprocess, shutil, etc.
  - Third-party: requests, PIL (from Pillow), etc. (ONLY if installed)
  - DO NOT assume imports - explicitly add them at the top of the file
  - Common mistake: Using json.dumps() without 'import json'
  - Common mistake: Using Path() without 'from pathlib import Path'
  - Common mistake: Using datetime without 'from datetime import datetime'

⚠️  GMAIL & CALENDAR CREDENTIALS ACCESS:
For Gmail workflows (mail:*):
  - Import: from agent.skills.mail.client import GmailClient
  - Usage: client = GmailClient()  # Automatically handles OAuth tokens
  - Token location: ~/.cloneai/tokens/gmail_token.json
  - Scopes: gmail.readonly, gmail.compose, gmail.send, gmail.modify
  - Methods available:
    * client.list_messages(max_results=10, query="") → List[Dict] with id, from, subject, date, body
    * client.get_full_message(message_id) → Dict with full email details
    * client.send_message(to, subject, body, cc=None, bcc=None, attachments=None)
    * client.create_draft(to, subject, body, cc=None, bcc=None)
    * client.reply_to_message(message_id, body)
  - IMPORTANT: list_messages returns Dict with keys: id, from, subject, date, snippet, body
  - ALWAYS check if list returns empty before accessing [0]

For Calendar workflows (calendar:*):
  - Import: from agent.tools.calendar import CalendarClient
  - Usage: client = CalendarClient()  # Automatically handles OAuth tokens
  - Token location: ~/.cloneai/tokens/calendar_token.json
  - Scopes: calendar, calendar.events
  - Methods: create_event, list_events, delete_event, update_event

⚠️  NOTE: There is NO 'agent.tools.search' module - use 'agent.tools.web_search' instead!
⚠️  NOTE: There is NO 'agent.tools.mail' module - use 'agent.skills.mail.client' instead!

⚠️  LLM USAGE - run_ollama() function:
  - Correct: run_ollama(prompt, profile=LOCAL_PLANNER) or run_ollama(prompt, profile=LOCAL_COMMAND_CLASSIFIER)
  - Import profile: from agent.config.runtime import LOCAL_PLANNER, LOCAL_COMMAND_CLASSIFIER
  - DO NOT use format="json" parameter - it doesn't exist!
  - Instead, ask for JSON in the prompt text itself

⚠️  FILE SAVING - Use pathlib, NOT DocumentManager:
  - For saving files (PDFs, PPTX, images, etc.), save directly to artifacts/ folder
  - Pattern:
    ```python
    import pathlib
    artifacts_dir = pathlib.Path.cwd() / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    file_path = artifacts_dir / filename
    # ... save to file_path ...
    ```
  - DO NOT use DocumentManager, temp files, or upload methods
  - DO NOT use tempfile.TemporaryDirectory() for final output
"""
        
        tool_section = tool_imports + "\n" + ("\n".join(tool_hints[:3]) if tool_hints else "(search agent/tools for helpers)")

        # Previous errors (only last 2)
        error_section = ""
        if previous_errors:
            recent = previous_errors[-2:]
            error_section = f"\n\nPrevious errors:\n" + "\n".join(f"  - {e}" for e in recent)

        # Determine category dynamically from existing workflows in this namespace
        category = self._get_category_for_namespace(namespace, context)

        # User context from LLM (crucial for understanding intent!)
        context_section = ""
        if recipe.user_context:
            context_section = f"""
USER INTENT & CONTEXT:
{recipe.user_context}

⚠️  CRITICAL: Read the above context carefully! It explains what the user is trying to do,
what parameters should be used (e.g., URL vs file path), and the expected behavior.
Generate code that matches this intent, not just the command name!
"""

        user_prompt = f"""Generate a CloneAI workflow module.

Command: {command_key}
Summary: {recipe.summary}
Description: {recipe.description}
{context_section}
Available tools:
{tool_section or "  (search agent/tools for helpers)"}

Example workflow:
{sample_workflow or "  # (no example available)"}

Output JSON (required):
{{
  "module_code": "Full Python code for {module_path}",
  "notes": ["Implementation notes"],
  "summary": "One-line summary"
}}

Requirements:
- ⚠️  CRITICAL: Include ALL necessary imports at the top (json, os, pathlib, datetime, typing, etc.)
- ⚠️  DOUBLE-CHECK: Every function/class used must have a corresponding import statement
- Use @register_workflow decorator directly on handler function
- Handler signature: def {namespace}_{recipe.name}_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str
- Include metadata with "usage" field showing command syntax
- Include "category" in metadata for proper grouping (use: "{category}") or if doesn't exist, create it.
- Use ParameterSpec for arguments with defaults
- Implement REAL working logic (NO placeholders, TODOs, or "not implemented" messages)
- Handle errors gracefully with informative messages
- DO NOT generate tests
- ⚠️  VERIFY all imports exist! Check the "Available tools" section for correct module paths
- Common mistake: using 'agent.tools.search' (WRONG) instead of 'agent.tools.web_search' (CORRECT)
- Common mistake: Using json.dumps() without 'import json' at the top
- Common mistake: Using Path() without 'from pathlib import Path'
- ⚠️  FILE PATH HANDLING: When working with files (reading/writing/modifying):
  * CloneAI saves created files in 'artifacts/' folder by default
  * If file path is just a filename (e.g., "file.pptx"), check both current directory AND artifacts/ folder
  * Use this pattern for file existence checks:
    ```python
    import pathlib
    if not os.path.isfile(file_path):
        artifacts_path = pathlib.Path.cwd() / "artifacts" / file_path
        if artifacts_path.exists():
            file_path = str(artifacts_path)
        else:
            return f"Error: File '{{file_path}}' not found"
    ```
  * This ensures workflows can find files created by other CloneAI commands

Correct pattern:
```python
from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any

@register_workflow(
    namespace="{namespace}",
    name="{recipe.name}",
    summary="{recipe.summary}",
    description="{recipe.description}",
    parameters=(
        ParameterSpec(name="arg1", description="...", type=str, required=True),
    ),
    metadata={{
        "category": "{category}",
        "usage": "{command_key} arg1:VALUE",
        "examples": ["Example: {command_key} arg1:test"],
    }}
)
def {namespace}_{recipe.name}_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    arg1 = params.get("arg1")
    # Real implementation here - use tools from agent.tools
    return f"Result: {{arg1}}"
```{error_section}

Respond with JSON only (no markdown fences)."""

        system_prompt = """You are a senior Python engineer generating production-ready workflow modules.
Output must be valid JSON matching the required schema.
Implement real functionality - no placeholders or TODO comments."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


__all__ = [
    "GPTWorkflowGenerator",
    "GPTWorkflowResult",
    "GPTWorkflowError",
    "GeneratedArtifact",
    "WorkflowGenerationContext",
]
