from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import os
import stat
import datetime

@register_workflow(
    namespace="system",
    name="scan_directory",
    summary="Auto-generated workflow for `system:scan_directory`",
    description="Implements the CLI command `system:scan_directory`. Scans a directory and returns a list of files and subdirectories with metadata.",
    parameters=(
        ParameterSpec(
            name="path",
            description="Path to the directory to scan.",
            type=str,
            required=True
        ),
        ParameterSpec(
            name="recursive",
            description="Whether to scan directories recursively (default: False).",
            type=bool,
            required=False,
            default=False
        ),
        ParameterSpec(
            name="show_hidden",
            description="Include hidden files and directories (default: False).",
            type=bool,
            required=False,
            default=False
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "system:scan_directory path:DIR [recursive:True|False] [show_hidden:True|False]",
        "examples": [
            "system:scan_directory path:/tmp",
            "system:scan_directory path:/var/log recursive:True show_hidden:True"
        ],
    }
)
def system_scan_directory_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    path = params.get("path")
    recursive = params.get("recursive", False)
    show_hidden = params.get("show_hidden", False)

    if not isinstance(path, str) or not path:
        return "Error: 'path' parameter must be a non-empty string."

    if not os.path.exists(path):
        return f"Error: Path does not exist: {path}"
    if not os.path.isdir(path):
        return f"Error: Path is not a directory: {path}"

    def is_hidden(filepath: str) -> bool:
        return os.path.basename(filepath).startswith('.')

    def scan_dir(dir_path: str) -> list:
        entries = []
        try:
            with os.scandir(dir_path) as it:
                for entry in it:
                    if not show_hidden and is_hidden(entry.name):
                        continue
                    try:
                        stat_info = entry.stat(follow_symlinks=False)
                        entry_info = {
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": entry.is_dir(follow_symlinks=False),
                            "is_file": entry.is_file(follow_symlinks=False),
                            "is_symlink": entry.is_symlink(),
                            "size": stat_info.st_size,
                            "mode": oct(stat_info.st_mode),
                            "mtime": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        }
                        entries.append(entry_info)
                    except Exception as e:
                        entries.append({
                            "name": entry.name,
                            "path": entry.path,
                            "error": f"Failed to stat entry: {e}"
                        })
        except Exception as e:
            entries.append({
                "name": dir_path,
                "path": dir_path,
                "error": f"Failed to scan directory: {e}"
            })
        return entries

    results = []
    if recursive:
        for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
            if not show_hidden:
                # Filter out hidden directories in-place
                dirs[:] = [d for d in dirs if not is_hidden(d)]
            dir_entries = scan_dir(root)
            results.extend(dir_entries)
    else:
        results = scan_dir(path)

    import json
    return json.dumps({
        "scanned_path": path,
        "recursive": recursive,
        "show_hidden": show_hidden,
        "entries": results
    }, indent=2)
