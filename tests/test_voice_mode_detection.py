import pytest

from agent.cli import _detect_voice_mode_intent


@pytest.mark.parametrize(
    "instruction",
    [
        "activate voice mode",
        "please start voice mode now",
        "enable listening mode",
        "could you turn on voice mode?",
    ],
)
def test_detect_voice_mode_activation(instruction: str) -> None:
    assert _detect_voice_mode_intent(instruction) == "activate"


@pytest.mark.parametrize(
    "instruction",
    [
        "shutdown voice mode",
        "please shut down voice mode",
        "stop listening mode",
        "can you turn off voice mode?",
    ],
)
def test_detect_voice_mode_deactivation(instruction: str) -> None:
    assert _detect_voice_mode_intent(instruction) == "deactivate"


@pytest.mark.parametrize(
    "instruction",
    [
        "voice modulation tips",
        "what is voice mode",
        "is listening mode useful?",
        "",
    ],
)
def test_detect_voice_mode_none(instruction: str) -> None:
    assert _detect_voice_mode_intent(instruction) is None
