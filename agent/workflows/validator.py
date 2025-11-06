"""
Workflow Code Validator

Security validator for GPT-generated workflow code.
Checks for potentially dangerous patterns before execution.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Tuple

# Security configuration
FORBIDDEN_IMPORTS = [
    "os.system",
    "subprocess.Popen", 
    "subprocess.call",
    "eval",
    "exec",
    "__import__",
    "compile"
]

FORBIDDEN_MODULES = [
    "ctypes",      # Low-level system calls
    "winreg",      # Windows registry
    "pty",         # Pseudo-terminals
    "socket",      # Raw networking (requests/urllib are OK)
    "pickle",      # Arbitrary code execution
    "shelve",      # Uses pickle internally
]

ALLOWED_MODULES = [
    "requests",
    "bs4",
    "beautifulsoup4",
    "pandas",
    "numpy",
    "PIL",
    "pillow",
    "openpyxl",
    "python-pptx",
    "PyPDF2",
    "pdf2docx",
    "docx",
    "python-docx",
    "json",
    "datetime",
    "pathlib",
    "typing",
    "dataclasses",
    "collections",
    "itertools",
    "functools",
    "re",
    "math",
]


def validate_workflow_code(code: str) -> Tuple[bool, List[str]]:
    """
    Validate generated workflow code for security issues.
    
    Args:
        code: Python source code to validate
    
    Returns:
        (is_safe, list_of_issues)
    """
    issues = []
    
    # Parse code into AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]
    
    # Check for forbidden imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES:
                    issues.append(f"Forbidden module import: {alias.name}")
        
        elif isinstance(node, ast.ImportFrom):
            if node.module in FORBIDDEN_MODULES:
                issues.append(f"Forbidden module import: {node.module}")
            
            # Check for dangerous functions from os/subprocess
            if node.module == "os":
                for alias in node.names:
                    if alias.name in ["system", "popen", "spawn"]:
                        issues.append(f"Forbidden function import: os.{alias.name}")
            
            if node.module == "subprocess":
                for alias in node.names:
                    if alias.name in ["Popen", "call", "run"]:
                        issues.append(f"Forbidden function import: subprocess.{alias.name}")
        
        # Check for eval/exec/compile calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ["eval", "exec", "compile", "__import__"]:
                    issues.append(f"Forbidden function call: {node.func.id}()")
            
            # Check for dangerous attribute calls
            elif isinstance(node.func, ast.Attribute):
                # os.system(), os.popen(), etc.
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "os" and node.func.attr in ["system", "popen"]:
                        issues.append(f"Forbidden call: os.{node.func.attr}()")
    
    # Check for suspicious string patterns
    suspicious_patterns = [
        (r'rm\s+-rf', "Dangerous shell command: rm -rf"),
        (r'del\s+/[sS]', "Dangerous Windows delete command"),
        (r'format\s+[A-Za-z]:', "Dangerous format command"),
        (r'dd\s+if=', "Dangerous dd command"),
        (r'/etc/passwd', "Access to system password file"),
        (r'sudo\s+', "Sudo command usage"),
    ]
    
    for pattern, description in suspicious_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(f"Suspicious pattern detected: {description}")
    
    return len(issues) == 0, issues


def save_workflow_safely(
    workflow_code: str,
    filename: str,
    force: bool = False
) -> Tuple[bool, str, List[str]]:
    """
    Validate and save workflow with security checks.
    
    Args:
        workflow_code: Python source code
        filename: Filename (should end with .py)
        force: Skip validation if True (dangerous!)
    
    Returns:
        (success, filepath, issues)
    """
    issues = []
    
    # Validate code unless forced
    if not force:
        is_safe, validation_issues = validate_workflow_code(workflow_code)
        if not is_safe:
            return False, "", validation_issues
    
    # Ensure filename is valid
    if not filename.endswith(".py"):
        filename += ".py"
    
    # Remove any path traversal attempts
    filename = Path(filename).name
    
    # Get custom workflows directory
    custom_dir = Path.home() / ".clai" / "workflows" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = custom_dir / filename
    
    # Check if file already exists
    if filepath.exists():
        issues.append(f"Warning: Overwriting existing workflow: {filename}")
    
    # Save file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(workflow_code)
        
        return True, str(filepath), issues
        
    except Exception as e:
        return False, "", [f"Failed to save workflow: {e}"]


def load_workflow_safely(filepath: str) -> Tuple[bool, str, List[str]]:
    """
    Load and validate a workflow file.
    
    Args:
        filepath: Path to workflow file
    
    Returns:
        (success, code, issues)
    """
    path = Path(filepath)
    
    # Security: Only allow loading from custom workflows directory
    custom_dir = Path.home() / ".clai" / "workflows" / "custom"
    try:
        path.resolve().relative_to(custom_dir.resolve())
    except ValueError:
        return False, "", ["Cannot load workflow from outside custom directory"]
    
    if not path.exists():
        return False, "", [f"File not found: {filepath}"]
    
    try:
        code = path.read_text(encoding="utf-8")
        is_safe, issues = validate_workflow_code(code)
        
        if not is_safe:
            return False, code, issues
        
        return True, code, []
        
    except Exception as e:
        return False, "", [f"Failed to load workflow: {e}"]


def get_workflow_info(filepath: str) -> dict:
    """
    Extract metadata from a workflow file.
    
    Returns:
        {
            "filename": str,
            "path": str,
            "size": int,
            "created": str,
            "modified": str,
            "is_safe": bool,
            "issues": List[str]
        }
    """
    path = Path(filepath)
    
    if not path.exists():
        return {"error": f"File not found: {filepath}"}
    
    try:
        stats = path.stat()
        code = path.read_text(encoding="utf-8")
        is_safe, issues = validate_workflow_code(code)
        
        return {
            "filename": path.name,
            "path": str(path),
            "size": stats.st_size,
            "created": stats.st_ctime,
            "modified": stats.st_mtime,
            "is_safe": is_safe,
            "issues": issues,
            "lines": len(code.splitlines())
        }
        
    except Exception as e:
        return {"error": str(e)}


__all__ = [
    "validate_workflow_code",
    "save_workflow_safely",
    "load_workflow_safely",
    "get_workflow_info"
]
