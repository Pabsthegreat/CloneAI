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
            resp = client.responses.create(
                model=self.model,                     # e.g., "gpt-4.1" or "gpt-4o-mini"
                input=input_text,                     # direct text input
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                store=True,
                metadata={
                    "component": "workflow_generator",
                    "command": recipe.command_key(),
                    "namespace": recipe.namespace,
                },
            )
            
            # Extract and display token usage information
            usage = getattr(resp, "usage", None)
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)
                
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

        # Prefer the convenience prop; fall back if not present
        response_text = getattr(resp, "output_text", None)
        if not response_text:
            # Fallback: stitch text parts from the structured "output"
            try:
                parts: List[str] = []
                for item in getattr(resp, "output", []) or []:
                    for c in getattr(item, "content", []) or []:
                        if getattr(c, "type", "") == "output_text":
                            parts.append(getattr(c, "text", ""))
                response_text = "".join(parts).strip()
            except Exception:
                response_text = ""

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
        
        tool_section = "\n".join(tool_hints[:3])  # Max 3 tools

        # Previous errors (only last 2)
        error_section = ""
        if previous_errors:
            recent = previous_errors[-2:]
            error_section = f"\n\nPrevious errors:\n" + "\n".join(f"  - {e}" for e in recent)

        # Determine category based on namespace
        category_map = {
            "mail": "MAIL COMMANDS",
            "calendar": "CALENDAR COMMANDS",
            "task": "SCHEDULER COMMANDS",
            "tasks": "SCHEDULER COMMANDS",
            "doc": "DOCUMENT COMMANDS",
            "convert": "DOCUMENT COMMANDS",
            "merge": "DOCUMENT COMMANDS",
            "system": "GENERAL COMMANDS",
            "math": "MATH COMMANDS",
            "text": "TEXT COMMANDS",
        }
        category = category_map.get(namespace, "OTHER COMMANDS")

        user_prompt = f"""Generate a CloneAI workflow module.

Command: {command_key}
Summary: {recipe.summary}
Description: {recipe.description}

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
- Use @register_workflow decorator directly on handler function
- Handler signature: def {namespace}_{recipe.name}_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str
- Include metadata with "usage" field showing command syntax
- Include "category" in metadata for proper grouping (use: "{category}") or if doesn't exist, create it.
- Use ParameterSpec for arguments with defaults
- Implement REAL working logic (NO placeholders, TODOs, or "not implemented" messages)
- Handle errors gracefully with informative messages
- DO NOT generate tests

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
