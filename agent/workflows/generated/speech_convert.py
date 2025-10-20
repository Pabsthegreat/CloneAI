from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import pathlib
import os
import pyttsx3

@register_workflow(
    namespace="speech",
    name="convert",
    summary="Auto-generated workflow for `speech:convert`",
    description="Implements the CLI command `speech:convert text:\"Diwali, also known as the Festival of Lights, is...\" accent:british`. Converts input text to speech audio with the specified accent and saves it as a WAV file in the artifacts directory.",
    parameters=(
        ParameterSpec(name="text", description="Text to convert to speech.", type=str, required=True),
        ParameterSpec(name="accent", description="Accent for speech synthesis (e.g., 'british', 'american').", type=str, required=False, default="british"),
        ParameterSpec(name="filename", description="Optional output filename (WAV). If not provided, a name will be auto-generated.", type=str, required=False, default=None),
    ),
    metadata={
        "category": "SPEECH COMMANDS",
        "usage": "speech:convert text:\"<TEXT>\" accent:<british|american> [filename:<output.wav>]",
        "examples": [
            "speech:convert text:\"Diwali, also known as the Festival of Lights, is...\" accent:british",
            "speech:convert text:\"Hello world!\" accent:american filename:greeting.wav"
        ],
    }
)
def speech_convert_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    text = params.get("text")
    accent = params.get("accent", "british").lower()
    filename = params.get("filename")

    if not text or not isinstance(text, str) or not text.strip():
        return "Error: 'text' parameter is required and must be non-empty."

    # Prepare output filename
    if filename:
        if not filename.lower().endswith('.wav'):
            filename += '.wav'
    else:
        safe_text = text[:20].replace(' ', '_').replace('"', '').replace("'", '')
        filename = f"speech_{safe_text}_{accent}.wav"
    artifacts_dir = pathlib.Path.cwd() / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    file_path = artifacts_dir / filename

    # Initialize pyttsx3 engine
    try:
        engine = pyttsx3.init()
    except Exception as e:
        return f"Error: Could not initialize speech engine: {e}"

    # Set accent/voice
    voices = engine.getProperty('voices')
    selected_voice = None
    accent_map = {
        'british': ['en-gb', 'english_rp', 'english', 'english - british'],
        'american': ['en-us', 'english-us', 'english - american', 'english-us'],
    }
    accent_keys = accent_map.get(accent, [])
    for voice in voices:
        for key in accent_keys:
            if key in voice.id.lower() or key in voice.name.lower():
                selected_voice = voice.id
                break
        if selected_voice:
            break
    if not selected_voice:
        # Fallback: use first English voice
        for voice in voices:
            if 'en' in voice.id.lower() or 'english' in voice.name.lower():
                selected_voice = voice.id
                break
    if selected_voice:
        engine.setProperty('voice', selected_voice)
    else:
        # If no English voice found, use default
        pass

    # Synthesize and save
    try:
        engine.save_to_file(text, str(file_path))
        engine.runAndWait()
    except Exception as e:
        return f"Error: Failed to synthesize speech: {e}"

    if not file_path.exists():
        return f"Error: Speech synthesis did not produce output file: {file_path}"

    return f"Speech audio saved to: {file_path}"
