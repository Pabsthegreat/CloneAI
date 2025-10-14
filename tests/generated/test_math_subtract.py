import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowValidationError

@pytest.fixture(scope="module")
def registry():
    from agent.workflows import generated
    return WorkflowRegistry()

@pytest.fixture(scope="module")
def subtract_spec(registry):
    from agent.workflows.generated import math_subtract
    # The registry auto-registers on import, so we can fetch by key
    return registry._workflows["math:subtract"]

def test_basic_subtraction(subtract_spec):
    args = subtract_spec.parse_arguments("a:50 b:100")
    ctx = None  # Handler does not use context for this workflow
    output = subtract_spec.handler(ctx, args)
    assert output == "Result: -50"

def test_float_subtraction(subtract_spec):
    args = subtract_spec.parse_arguments("a:5.5 b:2.2")
    output = subtract_spec.handler(None, args)
    assert output == "Result: 3.3"

def test_zero_result(subtract_spec):
    args = subtract_spec.parse_arguments("a:10 b:10")
    output = subtract_spec.handler(None, args)
    assert output == "Result: 0"

def test_missing_a_raises(subtract_spec):
    args = subtract_spec.parse_arguments("b:5")
    with pytest.raises(WorkflowValidationError) as e:
        subtract_spec.handler(None, args)
    assert "Parameter 'a' is required" in str(e.value)

def test_missing_b_raises(subtract_spec):
    args = subtract_spec.parse_arguments("a:5")
    with pytest.raises(WorkflowValidationError) as e:
        subtract_spec.handler(None, args)
    assert "Parameter 'b' is required" in str(e.value)

def test_invalid_type_raises(subtract_spec):
    args = subtract_spec.parse_arguments("a:foo b:2")
    with pytest.raises(WorkflowValidationError):
        subtract_spec.handler(None, args)
