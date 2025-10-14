import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowValidationError

def get_registry():
    from agent.workflows.generated import text_reverse  # noqa: F401
    return WorkflowRegistry()

def test_text_reverse_basic():
    from agent.workflows.generated import text_reverse  # noqa: F401
    registry = WorkflowRegistry()
    spec = registry._workflows["text:reverse"]
    args = spec.parse_arguments("Hello")
    ctx = type("DummyCtx", (), {"raw_command": "text:reverse input:Hello", "registry": registry, "extras": {}})()
    result = spec.handler(ctx, args)
    assert result == "olleH"

def test_text_reverse_empty():
    from agent.workflows.generated import text_reverse  # noqa: F401
    registry = WorkflowRegistry()
    spec = registry._workflows["text:reverse"]
    args = spec.parse_arguments("")
    ctx = type("DummyCtx", (), {"raw_command": "text:reverse input:", "registry": registry, "extras": {}})()
    result = spec.handler(ctx, args)
    assert result == ""

def test_text_reverse_whitespace():
    from agent.workflows.generated import text_reverse  # noqa: F401
    registry = WorkflowRegistry()
    spec = registry._workflows["text:reverse"]
    args = spec.parse_arguments("  abc def  ")
    ctx = type("DummyCtx", (), {"raw_command": "text:reverse input:  abc def  ", "registry": registry, "extras": {}})()
    result = spec.handler(ctx, args)
    assert result == "  fed cba  "

def test_text_reverse_missing_param():
    from agent.workflows.generated import text_reverse  # noqa: F401
    registry = WorkflowRegistry()
    spec = registry._workflows["text:reverse"]
    ctx = type("DummyCtx", (), {"raw_command": "text:reverse", "registry": registry, "extras": {}})()
    with pytest.raises(WorkflowValidationError):
        spec.handler(ctx, {})
