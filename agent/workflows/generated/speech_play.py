from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import pathlib
import os
import sys
import platform
import subprocess

@register_workflow(
    namespace="speech",
    name="play",
    summary="Auto-generated workflow for `speech:play`",
    description="Implements the CLI command `speech:play`. Plays an existing audio file (WAV) from the current directory or artifacts/ folder.",
    parameters=(
        ParameterSpec(name="filename", description="Name of the audio file to play (must be a .wav file)", type=str, required=True),
    ),
    metadata={
        "category": "SPEECH COMMANDS",
        "usage": "speech:play filename:diwali_british.wav",
        "examples": ["speech:play filename:diwali_british.wav"],
    }
)
def speech_play_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    filename = params.get("filename")
    if not filename:
        return "Error: No filename provided."
    
    # Only allow .wav files for safety
    if not filename.lower().endswith('.wav'):
        return f"Error: Only .wav files are supported. Got: {filename}"

    # Try current directory first
    file_path = pathlib.Path(filename)
    if not file_path.is_file():
        # Try artifacts/ directory
        artifacts_path = pathlib.Path.cwd() / "artifacts" / filename
        if artifacts_path.is_file():
            file_path = artifacts_path
        else:
            return f"Error: File '{filename}' not found in current directory or artifacts/ folder."

    # Platform-specific playback
    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["afplay", str(file_path)], check=True)
        elif system == "Windows":
            import winsound
            winsound.PlaySound(str(file_path), winsound.SND_FILENAME)
        else:  # Assume Linux/Unix
            # Try aplay, then paplay, then ffplay
            played = False
            for player in (["aplay"], ["paplay"], ["ffplay", "-autoexit", "-nodisp"]):
                try:
                    subprocess.run(player + [str(file_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    played = True
                    break
                except FileNotFoundError:
                    continue
                except subprocess.CalledProcessError:
                    continue
            if not played:
                return "Error: No suitable audio player found (tried aplay, paplay, ffplay). Please install one."
    except Exception as e:
        return f"Error: Failed to play audio file: {e}"

    return f"Audio file '{filename}' has been played successfully."
