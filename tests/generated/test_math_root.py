import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowExecutionError, WorkflowValidationError
from agent.workflows.generated import math_root

def get_registry():
    return WorkflowRegistry()

def test_math_root_basic():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root a:144", "registry": registry, "extras": {}})()
    params = {"a": 144}
    output = spec.handler(ctx, params)
    assert "square root of 144" in output
    assert "12.0" in output

def test_math_root_float():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root a:2.25", "registry": registry, "extras": {}})()
    params = {"a": 2.25}
    output = spec.handler(ctx, params)
    assert "square root of 2.25" in output
    assert "1.5" in output

def test_math_root_zero():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root a:0", "registry": registry, "extras": {}})()
    params = {"a": 0}
    output = spec.handler(ctx, params)
    assert "square root of 0" in output
    assert output.strip().endswith("0.0.")

def test_math_root_negative():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root a:-9", "registry": registry, "extras": {}})()
    params = {"a": -9}
    with pytest.raises(WorkflowValidationError) as excinfo:
        spec.handler(ctx, params)
    assert "negative number" in str(excinfo.value)

def test_math_root_missing_param():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root", "registry": registry, "extras": {}})()
    params = {}
    with pytest.raises(WorkflowValidationError) as excinfo:
        spec.handler(ctx, params)
    assert "Missing required parameter" in str(excinfo.value)

def test_math_root_invalid_type():
    registry = get_registry()
    spec = registry._workflows["math:root"]
    ctx = type("DummyCtx", (), {"raw_command": "math:root a:foo", "registry": registry, "extras": {}})()
    params = {"a": "foo"}
    with pytest.raises(WorkflowValidationError) as excinfo:
        spec.handler(ctx, params)
    assert "must be a number" in str(excinfo.value)
