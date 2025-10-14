import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowValidationError

def get_registry():
    # Import triggers registration
    import agent.workflows.generated.math_add
    return WorkflowRegistry()

def test_math_add_basic():
    import agent.workflows.generated.math_add  # Ensure registration
    registry = get_registry()
    spec = registry._workflows["math:add"]
    args = spec.parse_arguments("a:15 b:27")
    ctx = type("DummyCtx", (), {"raw_command": "math:add a:15 b:27", "registry": registry, "extras": {}})()
    output = spec.handler(ctx, args)
    assert output == "The sum of 15 and 27 is 42."

def test_math_add_negative():
    import agent.workflows.generated.math_add
    registry = get_registry()
    spec = registry._workflows["math:add"]
    args = spec.parse_arguments("a:-5 b:10")
    ctx = type("DummyCtx", (), {"raw_command": "math:add a:-5 b:10", "registry": registry, "extras": {}})()
    output = spec.handler(ctx, args)
    assert output == "The sum of -5 and 10 is 5."

def test_math_add_missing_param():
    import agent.workflows.generated.math_add
    registry = get_registry()
    spec = registry._workflows["math:add"]
    ctx = type("DummyCtx", (), {"raw_command": "math:add a:1", "registry": registry, "extras": {}})()
    with pytest.raises(WorkflowValidationError) as excinfo:
        spec.handler(ctx, {"a": 1})
    assert "Missing required parameter: b" in str(excinfo.value)

def test_math_add_invalid_type():
    import agent.workflows.generated.math_add
    registry = get_registry()
    spec = registry._workflows["math:add"]
    ctx = type("DummyCtx", (), {"raw_command": "math:add a:foo b:2", "registry": registry, "extras": {}})()
    with pytest.raises(WorkflowValidationError):
        # parse_arguments will raise
        spec.parse_arguments("a:foo b:2")
