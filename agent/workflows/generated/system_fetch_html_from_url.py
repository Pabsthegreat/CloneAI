from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import requests
import os
from urllib.parse import urlparse

@register_workflow(
    namespace="system",
    name="fetch_html_from_url",
    summary="Auto-generated workflow for `system:fetch_html_from_url`",
    description="Implements the CLI command `system:fetch_html_from_url`. Fetches HTML content from a provided web URL and saves it to a local file.",
    parameters=(
        ParameterSpec(
            name="url",
            description="A valid web URL to fetch HTML from (e.g., https://example.com)",
            type=str,
            required=True
        ),
        ParameterSpec(
            name="file",
            description="Local file path where the HTML content will be saved (e.g., ./example.html)",
            type=str,
            required=True
        ),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "system:fetch_html_from_url url:URL file:LOCAL_PATH",
        "examples": [
            "Example: system:fetch_html_from_url url:https://example.com file:./example.html"
        ]
    }
)
def system_fetch_html_from_url_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    url = params.get("url")
    file_path = params.get("file")

    # Validate URL
    parsed_url = urlparse(url)
    if not (parsed_url.scheme in ("http", "https") and parsed_url.netloc):
        raise ValueError(f"Invalid URL provided: {url}")

    # Validate file path (basic check)
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError(f"Invalid file path provided: {file_path}")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}")

    # Ensure the directory exists
    dir_name = os.path.dirname(os.path.abspath(file_path))
    if dir_name and not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create directory '{dir_name}': {e}")

    try:
        with open(file_path, "w", encoding=response.encoding or "utf-8") as f:
            f.write(response.text)
    except Exception as e:
        raise RuntimeError(f"Failed to write HTML to file '{file_path}': {e}")

    return f"HTML content from '{url}' successfully saved to '{file_path}'."
