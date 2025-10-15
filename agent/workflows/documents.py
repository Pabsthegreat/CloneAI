"""Document processing workflows registered with the workflow registry."""

from __future__ import annotations

from typing import Any, Dict

from agent.tools.documents import (
    merge_pdf_files,
    merge_ppt_files,
    convert_pdf_to_docx,
    convert_docx_to_pdf,
    convert_ppt_to_pdf,
)
from agent.workflows import ParameterSpec, WorkflowContext, WorkflowValidationError, register_workflow


@register_workflow(
    namespace="doc",
    name="merge-pdf",
    summary="Merge multiple PDF files",
    description="Merges multiple PDF files into a single output file.",
    parameters=(
        ParameterSpec(
            name="files",
            description="Comma-separated list of PDF files to merge",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="output",
            description="Output file path",
            type=str,
            required=True,
        ),
    ),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "doc:merge-pdf files:FILE1,FILE2,... output:OUTPUT_FILE",
        "returns": "str",
        "examples": [
            "doc:merge-pdf files:doc1.pdf,doc2.pdf,doc3.pdf output:merged.pdf"
        ],
    },
)
def doc_merge_pdf_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for merging PDF files."""
    files_str = params.get("files")
    output = params.get("output")
    
    if not files_str or not output:
        raise WorkflowValidationError("'files' and 'output' are required")
    
    # Parse comma-separated files
    files = [f.strip() for f in files_str.split(',')]
    
    return merge_pdf_files(files, output)


@register_workflow(
    namespace="merge",
    name="ppt",
    summary="Interactive PowerPoint merge",
    description="Interactively merges PowerPoint presentations.",
    parameters=(),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "merge ppt",
        "returns": "str",
        "examples": ["merge ppt"],
    },
)
def merge_ppt_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for merging PowerPoint files."""
    # Interactive file selection
    import os
    
    print("Select PowerPoint files to merge (enter full paths, empty line to finish):")
    files = []
    while True:
        path = input(f"File {len(files) + 1}: ").strip()
        if not path:
            break
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
        files.append(path)
    
    if not files:
        return "No files selected"
    
    output = input("Output file path: ").strip()
    if not output:
        return "No output path provided"
    
    return merge_ppt_files(files, output)


@register_workflow(
    namespace="convert",
    name="pdf-to-docx",
    summary="Convert PDF to Word",
    description="Converts a PDF file to Word (DOCX) format.",
    parameters=(
        ParameterSpec(
            name="input",
            description="Input PDF file path",
            type=str,
            required=True,
            aliases=["file", "pdf"]
        ),
        ParameterSpec(
            name="output",
            description="Output DOCX file path (optional)",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "convert pdf-to-docx input:FILE [output:FILE]",
        "returns": "str",
        "examples": [
            "convert pdf-to-docx input:document.pdf",
            "convert pdf-to-docx input:document.pdf output:document.docx"
        ],
    },
)
def convert_pdf_to_docx_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for converting PDF to DOCX."""
    input_file = params.get("input")
    output_file = params.get("output")
    
    if not input_file:
        raise WorkflowValidationError("'input' file is required")
    
    return convert_pdf_to_docx(input_file, output_file)


@register_workflow(
    namespace="convert",
    name="docx-to-pdf",
    summary="Convert Word to PDF (Windows only)",
    description="Converts a Word (DOCX) file to PDF format. Windows only.",
    parameters=(
        ParameterSpec(
            name="input",
            description="Input DOCX file path",
            type=str,
            required=True,
            aliases=["file", "docx"]
        ),
        ParameterSpec(
            name="output",
            description="Output PDF file path (optional)",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "convert docx-to-pdf input:FILE [output:FILE]",
        "returns": "str",
        "examples": [
            "convert docx-to-pdf input:document.docx",
            "convert docx-to-pdf input:document.docx output:document.pdf"
        ],
    },
)
def convert_docx_to_pdf_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for converting DOCX to PDF."""
    input_file = params.get("input")
    output_file = params.get("output")
    
    if not input_file:
        raise WorkflowValidationError("'input' file is required")
    
    return convert_docx_to_pdf(input_file, output_file)


@register_workflow(
    namespace="convert",
    name="ppt-to-pdf",
    summary="Convert PPT to PDF (Windows only)",
    description="Converts a PowerPoint (PPT/PPTX) file to PDF format. Windows only.",
    parameters=(
        ParameterSpec(
            name="input",
            description="Input PPT/PPTX file path",
            type=str,
            required=True,
            aliases=["file", "ppt", "pptx"]
        ),
        ParameterSpec(
            name="output",
            description="Output PDF file path (optional)",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "convert ppt-to-pdf input:FILE [output:FILE]",
        "returns": "str",
        "examples": [
            "convert ppt-to-pdf input:presentation.pptx",
            "convert ppt-to-pdf input:slides.ppt output:slides.pdf"
        ],
    },
)
def convert_ppt_to_pdf_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for converting PPT to PDF."""
    input_file = params.get("input")
    output_file = params.get("output")
    
    if not input_file:
        raise WorkflowValidationError("'input' file is required")
    
    return convert_ppt_to_pdf(input_file, output_file)
