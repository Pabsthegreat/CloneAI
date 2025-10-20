"""
Image generation using OpenAI's GPT-5 with image_generation tools
"""

import os
import base64
from typing import Optional
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


def generate_image(
    prompt: str,
    *,
    filename: Optional[str] = None,
    output_dir: Optional[str] = None
) -> dict:
    """
    Generate an image using OpenAI's GPT-5 with image_generation tools.
    
    Args:
        prompt: Text description of the image to generate
        filename: Optional filename for the image (defaults to auto-generated from prompt)
        output_dir: Directory to save images (defaults to artifacts/)
    
    Returns:
        dict with keys:
            - success: bool
            - image_path: saved file path
            - error: error message if failed
    
    Example:
        result = generate_image("A sunset over mountains", filename="sunset.png")
        if result["success"]:
            print(f"Saved to: {result['image_path']}")
    """
    if OpenAI is None:
        return {
            "success": False,
            "error": "OpenAI library not installed. Run: pip install openai"
        }
    
    api_key = os.getenv("CLAI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OpenAI API key not found. Set OPENAI_API_KEY or CLAI_OPENAI_API_KEY environment variable."
        }
    
    # Set output directory
    if output_dir is None:
        output_dir = str(Path.cwd() / "artifacts")
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate filename if not provided
    if filename is None:
        safe_prompt = "".join(c for c in prompt[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"{safe_prompt}.png"
    
    # Ensure .png extension
    if not filename.lower().endswith('.png'):
        filename += '.png'
    
    filepath = Path(output_dir) / filename
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Generate image using GPT-5 with image_generation tool
        response = client.responses.create(
            model="gpt-5",
            input=f"Generate an image: {prompt}",
            tools=[{"type": "image_generation"}]
        )
        
        # Extract base64 image data from response
        image_data = [
            output.result 
            for output in response.output 
            if output.type == "image_generation_call"
        ]
        
        if not image_data:
            return {
                "success": False,
                "error": "No image data returned from API"
            }
        
        # Decode and save image
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(image_data[0]))
        
        return {
            "success": True,
            "image_path": str(filepath),
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


__all__ = ["generate_image"]
