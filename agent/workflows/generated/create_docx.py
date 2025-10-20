from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
from agent.tools.ollama_client import run_ollama
from agent.config.runtime import LOCAL_PLANNER
import pathlib
import docx
import os

@register_workflow(
    namespace="create",
    name="docx",
    summary="Auto-generated workflow for `create:docx`",
    description="Implements the CLI command `create:docx description:'500 word essay about Diwali' filename:deepawali_essay.docx`.",
    parameters=(
        ParameterSpec(name="description", description="Description of the document to generate (e.g., '500 word essay about Diwali')", type=str, required=True),
        ParameterSpec(name="filename", description="Filename for the generated .docx file (e.g., 'deepawali_essay.docx')", type=str, required=True),
    ),
    metadata={
        "category": "CREATE COMMANDS",
        "usage": "create:docx description:'500 word essay about Diwali' filename:deepawali_essay.docx",
        "examples": [
            "create:docx description:'500 word essay about Diwali' filename:deepawali_essay.docx"
        ]
    }
)
def create_docx_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    description = params.get("description")
    filename = params.get("filename")
    if not description or not filename:
        return "Error: Both 'description' and 'filename' parameters are required."
    if not filename.lower().endswith(".docx"):
        return "Error: Filename must end with .docx"
    try:
        # Generate essay content using LLM
        prompt = f"Write a {description}. The output should be a well-structured essay."
        essay = run_ollama(prompt, profile=LOCAL_PLANNER)
        if not essay or not isinstance(essay, str) or len(essay.strip()) < 100:
            return "Error: Failed to generate essay content."
        # Save to artifacts/ directory
        artifacts_dir = pathlib.Path.cwd() / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        file_path = artifacts_dir / filename
        # Create docx file
        doc = docx.Document()
        for para in essay.strip().split("\n\n"):
            doc.add_paragraph(para.strip())
        doc.save(str(file_path))
        return f"Success: DOCX file created at '{file_path}'"
    except Exception as e:
        return f"Error: Failed to create DOCX file. Details: {e}"
