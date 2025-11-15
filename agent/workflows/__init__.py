"""Workflow registration and execution utilities for CloneAI."""

from functools import lru_cache
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
from .catalog import LEGACY_NOTES

_GENERATED_PACKAGE = f"{__name__}.generated"


def load_builtin_workflows(modules: Iterable[str] | None = None) -> None:
    """
    Automatically discovers and imports all workflow modules in the workflows directory.
    Each module self-registers its workflows with the registry using @register_workflow decorators.
    
    Args:
        modules: Optional iterable of module names. If not provided, auto-discovers all .py files.
    """
    if modules is not None:
        # Explicit module list provided
        module_names = tuple(modules)
    else:
        # Auto-discover all workflow modules in this directory
        workflows_dir = Path(__file__).parent
        module_names = []
        
        for file_path in workflows_dir.glob("*.py"):
            # Skip special files
            if file_path.name.startswith("_") or file_path.stem in ("__init__", "registry", "catalog"):
                continue
            module_names.append(file_path.stem)
    
    # Import all discovered modules (they self-register via decorators)
    for module_name in module_names:
        try:
            import_module(f"{__name__}.{module_name}")
        except ImportError as e:
            # Log but don't fail - allow partial loading
            print(f"Warning: Failed to load workflow module '{module_name}': {e}")
    
    # Load generated workflows
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


@lru_cache(maxsize=2)
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
