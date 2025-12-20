from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
from agent.core.llm.ollama import run_ollama
from agent.config.runtime import LOCAL_PLANNER
import pathlib
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

@register_workflow(
    namespace="create",
    name="pdf",
    summary="Auto-generated workflow for `create:pdf`",
    description="Implements the CLI command `create:pdf`. Generates a professionally formatted PDF from a textual description.",
    parameters=(
        ParameterSpec(name="description", description="A detailed text description of the content to include in the PDF.", type=str, required=True),
        ParameterSpec(name="filename", description="The name of the output PDF file (e.g., 'diwali_introduction.pdf').", type=str, required=True),
    ),
    metadata={
        "category": "CREATE COMMANDS",
        "usage": "create:pdf description:'A 300-word introduction to Diwali' filename:diwali_introduction.pdf",
        "examples": [
            "create:pdf description:'A 300-word introduction to Diwali' filename:diwali_introduction.pdf"
        ]
    }
)
def create_pdf_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    description = params.get("description")
    filename = params.get("filename")
    if not description or not filename:
        return "Error: Both 'description' and 'filename' parameters are required."
    if not filename.lower().endswith(".pdf"):
        return "Error: Filename must end with .pdf"
    try:
        # Generate structured content using LLM
        prompt = (
            "You are a professional document writer. "
            "Given the following description, generate a well-structured, concise, and professionally formatted document. "
            "The document should have a clear heading, logical flow, and readable paragraphs. "
            "Do NOT include any metadata, references, or external data. "
            "Respond in JSON with the following structure: {\"title\": str, \"sections\": [{\"heading\": str, \"content\": str}]}. "
            f"Description: {description}"
        )
        llm_response = run_ollama(prompt, profile=LOCAL_PLANNER)
        import json
        try:
            doc_struct = json.loads(llm_response)
            title = doc_struct.get("title", "Document")
            sections = doc_struct.get("sections", [])
            if not sections:
                return "Error: LLM did not return any sections for the document."
        except Exception as e:
            return f"Error: Failed to parse LLM response as JSON: {e}\nRaw response: {llm_response}"

        # Prepare PDF path
        artifacts_dir = pathlib.Path.cwd() / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        file_path = artifacts_dir / filename

        # Build PDF
        doc = SimpleDocTemplate(str(file_path), pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []
        # Title
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 0.3 * inch))
        # Sections
        for section in sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            if heading:
                story.append(Paragraph(heading, styles["Heading2"]))
                story.append(Spacer(1, 0.15 * inch))
            if content:
                story.append(Paragraph(content, styles["BodyText"]))
                story.append(Spacer(1, 0.2 * inch))
        doc.build(story)
        return f"PDF created successfully: {file_path}"
    except Exception as e:
        return f"Error: Failed to generate PDF: {e}"
