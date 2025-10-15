from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import os
from bs4 import BeautifulSoup

@register_workflow(
    namespace="system",
    name="parse_html_content",
    summary="Parses HTML content from a local file and extracts readable text.",
    description="Implements the CLI command `system:parse_html_content file:/tmp/everythingresume.html`. Reads the specified HTML file, parses its content, and returns the extracted plain text.",
    parameters=(
        ParameterSpec(
            name="file",
            description="Path to the local HTML file (e.g., file:/tmp/everythingresume.html)",
            type=str,
            required=True
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "system:parse_html_content file:FILE_PATH",
        "examples": [
            "system:parse_html_content file:/tmp/everythingresume.html"
        ]
    }
)
def system_parse_html_content_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    file_uri = params.get("file")
    if not file_uri or not isinstance(file_uri, str):
        return "Error: 'file' parameter is required and must be a string."
    if not file_uri.startswith("file:"):
        return "Error: File path must start with 'file:'."
    file_path = file_uri[5:]
    if not os.path.isfile(file_path):
        return f"Error: File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        return f"Error reading file: {e}"
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script and style elements
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        result = "\n".join(lines)
        return result if result else "No readable text found in HTML."
    except Exception as e:
        return f"Error parsing HTML: {e}"
