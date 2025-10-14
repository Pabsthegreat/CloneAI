from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext, WorkflowValidationError
from typing import Dict, Any
import math

@register_workflow(
    namespace="math",
    name="root",
    summary="Auto-generated workflow for `math:root`",
    description="Implements the CLI command `math:root a:144`. Computes the positive square root of a given non-negative number.",
    parameters=(
        ParameterSpec(
            name="a",
            description="The number to compute the square root of (must be non-negative).",
            type=float,
            required=True,
            position=0,
        ),
    ),
    metadata={
        "usage": "math:root a:NUMBER",
        "examples": [
            "math:root a:144",
            "math:root a:2.25",
            "math:root a:0"
        ],
    },
)
def math_root_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    a = params.get("a")
    if a is None:
        raise WorkflowValidationError("Missing required parameter 'a'.")
    if not isinstance(a, (int, float)):
        raise WorkflowValidationError(f"Parameter 'a' must be a number, got {type(a).__name__}.")
    if a < 0:
        raise WorkflowValidationError("Cannot compute the square root of a negative number.")
    try:
        result = math.sqrt(a)
    except Exception as exc:
        raise WorkflowValidationError(f"Failed to compute square root: {exc}")
    return f"The square root of {a} is {result}."
