"""
Integration with OpenAI responses API for generating new workflow modules.
Uses the newer responses.create() API with direct text input/output.
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
    model: str = "gpt-4.1",           # better default for code + structure
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    max_output_tokens: int = 6000,
    ):
 
        self.api_key = api_key or os.getenv("CLAI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

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
        module_placeholder = f"agent/workflows/generated/{namespace}_{recipe.name}.py"

        sample_workflows = "\n\n".join(
            f"# File: {path}\n{textwrap.indent(code.strip(), '    ')}"
            for path, code in context.sample_workflows.items()
            if code.strip()
        )

        tool_summaries = "\n\n".join(
            f"# Tool: {path}\n{textwrap.indent(code.strip(), '    ')}"
            for path, code in context.tool_summaries.items()
            if code.strip()
        )

        error_section = ""
        if previous_errors:
            joined = "\n".join(f"- {err}" for err in previous_errors[-3:])
            error_section = f"\nPrevious attempt feedback:\n{joined}\n"

        user_prompt = textwrap.dedent(
            f"""
            You must implement a new CloneAI workflow command.

            Command: {command_key}
            Namespace: {recipe.namespace}
            Summary: {recipe.summary}
            Description: {recipe.description}

            Existing workflows (read-only): {', '.join(context.existing_workflows)}

            Project structure (truncated):
{textwrap.indent(context.project_tree.strip(), '    ')}

            Workflow registry (excerpt):
{textwrap.indent(context.registry_source.strip(), '    ')}

            Sample workflow modules:
{sample_workflows or '    # No sample workflows available'}

            Relevant tool modules:
{tool_summaries or '    # No tool modules provided'}

            Command reference (abbreviated):
{textwrap.indent(context.command_reference.strip(), '    ')}

            Output JSON schema (mandatory):
            {{
              "module_code": "Full Python module content for {module_placeholder}",
              "notes": ["bullet guidance for humans"],
              "summary": "One line summary of functionality"
            }}

            NOTE: DO NOT generate tests. Tests are unnecessary and waste tokens.

            Requirements:
            - The module must register the workflow using `@register_workflow` from `agent.workflows`.
            - Store the module at `{module_placeholder}` (no need to mention this in code).
            - The handler should accept `(ctx, params)` and return a human-readable string.
            - Use `ParameterSpec` for arguments with sensible defaults.
            - Prefer existing helper functions from `agent.tools` when possible; otherwise implement safe helpers within the module.
            - Include thorough error handling with informative messages.
            - Keep code concise and follow existing style.
            - Avoid placeholder text such as TODO; implement working logic or gracefully raise with explanation.
            - Do not modify existing files; only produce the module code in the JSON response.
            - ALWAYS include metadata with "usage" showing the command syntax with all required parameters.
            - The "usage" field helps the natural language parser understand how to construct commands.
            - DO NOT generate tests - they are unnecessary and waste tokens.

            CRITICAL - CORRECT REGISTRATION PATTERN:
            The @register_workflow decorator MUST be used directly on the handler function with parameters:

            CORRECT EXAMPLE:
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
                    ParameterSpec(
                        name="param1",
                        description="Description of param1",
                        type=str,
                        required=True,
                    ),
                ),
                metadata={{
                    "usage": "{namespace}:{recipe.name} param1:VALUE",
                    "examples": [
                        "Example: {namespace}:{recipe.name} param1:example_value"
                    ],
                }},
            )
            def {namespace}_{recipe.name}_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
                param1 = params.get("param1")
                # Implementation here
                return f"Result: {{param1}}"
            ```

            INCORRECT PATTERNS (DO NOT USE):
            ❌ @register_workflow without parameters on a function that returns WorkflowSpec
            ❌ Passing 'handler' as a parameter to @register_workflow
            ❌ Creating a separate registration function
            ❌ Calling register_workflow as a regular function

            The decorator pattern shown above is the ONLY correct way. Follow it exactly.

            {error_section}

            Respond with JSON only. No Markdown fences.
            """
        ).strip()

        system_prompt = textwrap.dedent(
            """
            You are GPT-4.1 acting as a senior Python engineer embedded in the CloneAI project.
            You generate production-ready workflow modules that integrate with an existing registry.
            Accuracy, deterministic output, and adherence to the required JSON schema are critical.
            Avoid extraneous prose; provide only the requested JSON data.
            """
        ).strip()

        return [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]


__all__ = [
    "GPTWorkflowGenerator",
    "GPTWorkflowResult",
    "GPTWorkflowError",
    "GeneratedArtifact",
    "WorkflowGenerationContext",
]
