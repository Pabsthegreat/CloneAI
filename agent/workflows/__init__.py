"""Workflow registration and execution utilities for CloneAI."""

from importlib import import_module
from pathlib import Path
from typing import Iterable, Tuple

from .registry import (
    ParameterSpec,
    WorkflowContext,
    WorkflowExecutionError,
    WorkflowExecutionResult,
    WorkflowNotFoundError,
    WorkflowRegistrationError,
    WorkflowRegistry,
    WorkflowSpec,
    WorkflowValidationError,
    register_workflow,
    registry,
)
from .catalog import LEGACY_SECTIONS, LEGACY_NOTES

_BUILTIN_WORKFLOW_MODULES: Tuple[str, ...] = (
    "mail",
)
_GENERATED_PACKAGE = f"{__name__}.generated"


def load_builtin_workflows(modules: Iterable[str] | None = None) -> None:
    """
    Import built-in workflow modules so they self-register with the registry.

    Args:
        modules: Optional iterable of module names relative to this package.
                 Defaults to the built-in catalog.
    """
    module_names = tuple(modules) if modules is not None else _BUILTIN_WORKFLOW_MODULES
    for module_name in module_names:
        import_module(f"{__name__}.{module_name}")
    load_generated_workflows()


def load_generated_workflows() -> None:
    """Load all dynamically generated workflow modules."""
    try:
        generated_pkg = import_module(_GENERATED_PACKAGE)
    except ModuleNotFoundError:
        return

    pkg_path = Path(getattr(generated_pkg, "__file__", "")).parent
    if not pkg_path.exists():
        return

    for file_path in sorted(pkg_path.glob("*.py")):
        if file_path.name.startswith("_") or file_path.stem == "__init__":
            continue
        module_name = f"{_GENERATED_PACKAGE}.{file_path.stem}"
        import_module(module_name)


def build_command_reference(include_legacy: bool = True) -> str:
    """
    Build a textual command reference that includes registered workflows and
    legacy commands not yet migrated to the registry.
    """
    load_builtin_workflows()

    # Collect registered workflow entries
    sections: dict[str, list[str]] = {}
    seen_usage: set[str] = set()

    for info in sorted(
        registry.export_command_info(),
        key=lambda item: (item["category"], item["usage"]),
    ):
        usage = info["usage"]
        seen_usage.add(usage.lower())
        line = f"- {usage}           # {info['summary']}"
        sections.setdefault(info["category"], []).append(line)

    if include_legacy:
        for category, commands in LEGACY_SECTIONS.items():
            for usage, description in commands:
                if usage.lower() in seen_usage:
                    continue
                line = f"- {usage}           # {description}"
                sections.setdefault(category, []).append(line)

    lines = ["CloneAI Command Reference:", "==========================", ""]

    for category in sorted(sections.keys()):
        lines.append(f"{category}:")
        lines.extend(sections[category])
        lines.append("")

    if include_legacy and LEGACY_NOTES.strip():
        lines.append(LEGACY_NOTES.strip())

    return "\n".join(lines).strip() + "\n"


__all__ = [
    "ParameterSpec",
    "WorkflowContext",
    "WorkflowExecutionError",
    "WorkflowExecutionResult",
    "WorkflowNotFoundError",
    "WorkflowRegistrationError",
    "WorkflowRegistry",
    "WorkflowSpec",
    "WorkflowValidationError",
    "register_workflow",
    "registry",
    "load_builtin_workflows",
    "load_generated_workflows",
    "build_command_reference",
]
