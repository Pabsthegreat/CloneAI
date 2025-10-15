from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import os

@register_workflow(
    namespace="system",
    name="count_lines_in_files",
    summary="Auto-generated workflow for `system:count_lines_in_files`",
    description="Implements the CLI command `system:count_lines_in_files`. Recursively counts the total number of non-blank, non-comment lines of code in all Python (.py) files within a given directory.",
    parameters=(
        ParameterSpec(
            name="path",
            description="Directory path to recursively scan for Python files.",
            type=str,
            required=True
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "system:count_lines_in_files path:YOUR_DIRECTORY_PATH",
        "examples": [
            "Example: system:count_lines_in_files path:agent/tools"
        ]
    }
)
def system_count_lines_in_files_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    import sys
    path = params.get("path")
    if not path or not isinstance(path, str):
        return "Error: 'path' parameter is required and must be a string."
    if not os.path.isdir(path):
        return f"Error: Provided path '{path}' is not a valid directory."
    
    total_lines = 0
    for root, _, files in os.walk(path):
        for fname in files:
            if fname.endswith('.py'):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            stripped = line.lstrip()
                            if not stripped:
                                continue  # skip blank lines
                            if stripped.startswith('#'):
                                continue  # skip comment lines
                            total_lines += 1
                except Exception as e:
                    # Log error, but continue with other files
                    ctx.log(f"Warning: Could not read file '{fpath}': {e}")
    return str(total_lines)
