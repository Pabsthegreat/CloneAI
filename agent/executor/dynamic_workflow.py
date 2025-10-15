"""
Dynamic workflow generation pipeline orchestrating GPT-4.1 and local integration.
"""

from __future__ import annotations

import importlib
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.config.runtime import REMOTE_GENERATOR_MAX_ATTEMPTS
from agent.executor.gpt_workflow import (
    GPTWorkflowError,
    GPTWorkflowGenerator,
    GeneratedArtifact,
    WorkflowGenerationContext,
)
from agent.executor.workflow_builder import WorkflowRecipe
from agent.tools import nl_parser
from agent.workflows import (
    build_command_reference,
    load_generated_workflows,
    registry as workflow_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_WORKFLOW_DIR = PROJECT_ROOT / "agent" / "workflows" / "generated"
GENERATED_TEST_DIR = PROJECT_ROOT / "tests" / "generated"


def _read_file(path: Path, char_limit: int = 4_000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if len(text) > char_limit:
        text = text[:char_limit] + "\n# ... truncated ..."
    return text


def _project_tree() -> str:
    """Return a shallow project tree to help GPT navigate files."""
    lines: List[str] = []
    targets = [
        ("agent", PROJECT_ROOT / "agent"),
        ("agent/workflows", PROJECT_ROOT / "agent" / "workflows"),
        ("agent/tools", PROJECT_ROOT / "agent" / "tools"),
        ("tests", PROJECT_ROOT / "tests"),
    ]
    for heading, path in targets:
        if not path.exists():
            continue
        lines.append(f"{heading}/")
        for item in sorted(path.iterdir()):
            if item.name.startswith("__pycache__"):
                continue
            if item.is_dir():
                lines.append(f"  {item.name}/")
            else:
                lines.append(f"  {item.name}")
        lines.append("")
    return "\n".join(lines).strip()


def _collect_sample_workflows(namespace: str) -> Dict[str, str]:
    samples: Dict[str, str] = {}
    
    # Include builtin workflow module if it exists
    candidate = PROJECT_ROOT / "agent" / "workflows" / f"{namespace}.py"
    if candidate.exists():
        samples[str(candidate.relative_to(PROJECT_ROOT))] = _read_file(candidate, 4_000)
    
    # For generated workflows, ONLY send summaries (not full code) to save tokens
    # This prevents exponential token growth as more workflows are created
    generated_dir = PROJECT_ROOT / "agent" / "workflows" / "generated"
    if generated_dir.exists():
        generated_summaries = []
        for generated_file in generated_dir.glob(f"{namespace}_*.py"):
            if generated_file.name != "__init__.py":
                # Extract just the filename, not the full code
                workflow_name = generated_file.stem.replace(f"{namespace}_", "")
                generated_summaries.append(f"{namespace}:{workflow_name}")
        
        if generated_summaries:
            summary_text = "Previously generated workflows in this namespace:\n" + "\n".join(f"- {w}" for w in generated_summaries)
            samples["generated_workflows_summary"] = summary_text
    
    # Always include registry for reference
    registry_path = PROJECT_ROOT / "agent" / "workflows" / "registry.py"
    samples[str(registry_path.relative_to(PROJECT_ROOT))] = _read_file(registry_path, 4_500)
    return samples


def _collect_tool_summaries(namespace: str) -> Dict[str, str]:
    summaries: Dict[str, str] = {}
    tool_path = PROJECT_ROOT / "agent" / "tools" / f"{namespace}.py"
    if tool_path.exists():
        summaries[str(tool_path.relative_to(PROJECT_ROOT))] = _read_file(tool_path, 4_000)
    return summaries


def _split_command(command: str) -> Tuple[str, str, str]:
    command = command.strip()
    if ":" not in command:
        raise ValueError("Commands must include namespace and action separated by ':'.")
    head, _, tail = command.partition(" ")
    namespace, _, action = head.partition(":")
    if not namespace or not action:
        raise ValueError("Invalid command format; expected namespace:action.")
    return namespace.strip(), action.strip(), tail.strip()


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _validate_module_code(module_code: str, module_path: Path) -> Optional[str]:
    try:
        compile(module_code, str(module_path), "exec")
    except SyntaxError as exc:
        return f"Syntax error: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return f"Compile error: {exc}"
    return None


@dataclass
class GenerationOutcome:
    success: bool
    output: Optional[str] = None
    notes: Optional[List[str]] = None
    summary: str = ""
    errors: Optional[List[str]] = None
    spec_namespace: Optional[str] = None
    spec_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class WorkflowGenerationManager:
    """Coordinates remote GPT generation and integration of new workflows."""

    def __init__(self, *, max_remote_calls_per_command: Optional[int] = None):
        self.generator = GPTWorkflowGenerator()
        self.max_remote_calls_per_command = (
            max_remote_calls_per_command
            if max_remote_calls_per_command is not None
            else REMOTE_GENERATOR_MAX_ATTEMPTS
        )
        self.attempts: Dict[str, int] = {}

    def can_attempt(self, command_key: str) -> bool:
        if not self.generator.is_configured():
            return False
        return self.attempts.get(command_key, 0) < self.max_remote_calls_per_command

    def ensure_workflow(
        self,
        command: str,
        *,
        extras: Optional[Dict[str, Any]] = None,
    ) -> GenerationOutcome:
        """Attempt to generate and execute a previously unsupported workflow."""
        namespace, action, _ = _split_command(command)
        command_key = f"{namespace}:{action}".lower()

        if not self.generator.is_configured():
            return GenerationOutcome(success=False, errors=["GPT integration is not configured."])

        attempt_count = self.attempts.get(command_key, 0)
        if attempt_count >= self.max_remote_calls_per_command:
            return GenerationOutcome(success=False, errors=["Remote generation quota reached for this command."])

        previous_errors: List[str] = []

        recipe = WorkflowRecipe(
            namespace=namespace,
            name=action,
            summary=f"Auto-generated workflow for `{command_key}`",
            description=f"Implements the CLI command `{command}`.",
            complexity="medium",
            notes={"force_tier": "cloud"},
        )

        context = WorkflowGenerationContext(
            command_reference=build_command_reference(),
            project_tree=_project_tree(),
            registry_source=_read_file(PROJECT_ROOT / "agent" / "workflows" / "registry.py", 4_500),
            sample_workflows=_collect_sample_workflows(namespace),
            tool_summaries=_collect_tool_summaries(namespace),
            existing_workflows=[
                spec.command_key() for spec in workflow_registry.list(namespace=None)
            ],
        )

        while attempt_count < self.max_remote_calls_per_command:
            attempt_count += 1
            self.attempts[command_key] = attempt_count
            
            print(f"\n{'='*60}")
            print(f"🔄 Workflow Generation Attempt {attempt_count}/{self.max_remote_calls_per_command}")
            print(f"Command: {command_key}")
            if previous_errors:
                print(f"⚠️  Retrying after {len(previous_errors)} previous error(s)")
            print(f"{'='*60}\n")
            
            try:
                result = self.generator.generate(recipe, context, previous_errors=previous_errors)
            except GPTWorkflowError as exc:
                previous_errors.append(str(exc))
                print(f"❌ Generation failed: {exc}\n")
                continue

            module_path = self._write_module(namespace, action, result.module_code)
            compile_error = _validate_module_code(result.module_code, module_path)
            if compile_error:
                previous_errors.append(compile_error)
                continue

            # Tests disabled to save tokens
            # self._write_tests(result.tests)

            try:
                self._import_generated_modules()
            except Exception as exc:  # pragma: no cover - import failures should be rare
                previous_errors.append(f"Import error: {exc}")
                continue

            try:
                nl_parser.refresh_command_reference()
            except Exception:
                # Refresh is best-effort; proceed even if it fails
                pass

            extras_dict = extras if extras is not None else {}
            try:
                exec_result = workflow_registry.execute(command, extras=extras_dict)
            except Exception as exc:  # pragma: no cover - runtime errors bubble for retry
                previous_errors.append(f"Execution after generation failed: {exc}")
                continue

            output = exec_result.output
            if not isinstance(output, str):
                output = str(output)

            suffix = "\n\n🤖 Workflow generated automatically via GPT-4.1 integration."
            final_output = output + suffix
            
            print(f"\n{'='*60}")
            print(f"✅ Workflow Generation SUCCESSFUL")
            print(f"{'='*60}")
            print(f"Command: {command_key}")
            print(f"Total Attempts: {attempt_count}")
            print(f"Module: {namespace}_{action}.py")
            print(f"Summary: {result.summary}")
            if result.notes:
                print(f"\nNotes:")
                for note in result.notes:
                    print(f"  • {note}")
            print(f"{'='*60}\n")
            
            return GenerationOutcome(
                success=True,
                output=final_output,
                notes=result.notes,
                summary=result.summary,
                spec_namespace=exec_result.spec.namespace,
                spec_name=exec_result.spec.name,
                arguments=exec_result.arguments,
            )

        print(f"\n{'='*60}")
        print(f"❌ Workflow Generation FAILED")
        print(f"{'='*60}")
        print(f"Command: {command_key}")
        print(f"Total Attempts: {attempt_count}")
        print(f"Errors encountered:")
        for i, error in enumerate(previous_errors, 1):
            print(f"  {i}. {error}")
        print(f"{'='*60}\n")
        
        return GenerationOutcome(success=False, errors=previous_errors)

    def _write_module(self, namespace: str, action: str, module_code: str) -> Path:
        _ensure_directory(GENERATED_WORKFLOW_DIR)
        module_path = GENERATED_WORKFLOW_DIR / f"{namespace}_{action}.py"
        module_path.write_text(module_code.strip() + "\n", encoding="utf-8")
        return module_path

    def _write_tests(self, tests: List[GeneratedArtifact]) -> None:
        if not tests:
            return
        _ensure_directory(GENERATED_TEST_DIR)
        for artifact in tests:
            path = (PROJECT_ROOT / Path(artifact.path)).resolve()
            if not str(path).startswith(str(PROJECT_ROOT)):
                continue  # safety: ignore paths outside repo
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(artifact.content.strip() + "\n", encoding="utf-8")

    @staticmethod
    def _import_generated_modules() -> None:
        importlib.invalidate_caches()
        load_generated_workflows()


dynamic_manager = WorkflowGenerationManager()


__all__ = ["dynamic_manager", "WorkflowGenerationManager", "GenerationOutcome"]
