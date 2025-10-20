"""
Image generation workflows using OpenAI GPT-5
"""

from __future__ import annotations
from typing import Dict, Any
from agent.workflows.registry import register_workflow, WorkflowContext, ParameterSpec
from agent.tools.image_generation import generate_image


@register_workflow(
    namespace="image",
    name="generate",
    summary="Generate an image from a text description",
    description="Creates an AI-generated image based on a text prompt using OpenAI GPT-5. Images are saved to the artifacts/ folder.",
    parameters=[
        ParameterSpec(name="prompt", type=str, required=True, description="Text description of the image to generate"),
        ParameterSpec(name="filename", type=str, required=False, description="Optional filename for the saved image (defaults to auto-generated)"),
    ],
    metadata={
        "category": "IMAGE COMMANDS",
        "usage": 'image:generate prompt:"DESCRIPTION" [filename:"NAME.png"]',
        "examples": [
            'image:generate prompt:"A sunset over mountains"',
            'image:generate prompt:"A futuristic city at night" filename:"city.png"',
            'image:generate prompt:"A cat playing with yarn" filename:"cat.png"'
        ]
    }
)
def workflow_generate_image(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """
    Generate an image from a text description.
    
    Args:
        ctx: Workflow execution context
        params: Parameters including prompt and optional filename
        
    Returns:
        Success message with image path or error message
    """
    prompt = params["prompt"]
    filename = params.get("filename")
    
    result = generate_image(prompt, filename=filename)
    
    if result["success"]:
        return f"✅ Image generated successfully: {result['image_path']}"
    else:
        error_msg = result.get("error", "Unknown error occurred")
        return f"❌ Failed to generate image: {error_msg}"


__all__ = ["workflow_generate_image"]
