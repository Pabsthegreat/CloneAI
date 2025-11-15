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

from agent.system_artifacts import ArtifactsManager


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
        output_dir: Directory to save images (defaults to ~/.clai/artifacts/images/)
    
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
    
    # Set output directory to centralized artifacts/images
    if output_dir is None:
        output_dir = str(ArtifactsManager.get_images_dir())
    
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
        
        # Generate image using DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Get the image URL
        image_url = response.data[0].url
        
        if not image_url:
            return {
                "success": False,
                "error": "No image URL returned from API"
            }
        
        # Download and save the image
        import requests
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            
            return {
                "success": True,
                "image_path": str(filepath),
            }
        else:
            return {
                "success": False,
                "error": f"Failed to download image: HTTP {img_response.status_code}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


__all__ = ["generate_image"]
