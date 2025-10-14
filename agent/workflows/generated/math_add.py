from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext, WorkflowValidationError
from typing import Dict, Any

@register_workflow(
    namespace="math",
    name="add",
    summary="Add two numbers together",
    description="Performs addition of two integers and returns the result.",
    parameters=(
        ParameterSpec(
            name="a",
            description="First number to add",
            type=int,
            required=True,
        ),
        ParameterSpec(
            name="b",
            description="Second number to add",
            type=int,
            required=True,
        ),
    ),
    metadata={
        "usage": "math:add a:NUMBER b:NUMBER",
        "examples": [
            "math:add a:5 b:3",
            "math:add a:100 b:250"
        ],
        "category": "MATH COMMANDS",
    },
)
def math_add_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    try:
        a = params.get("a")
        b = params.get("b")
        if a is None:
            raise WorkflowValidationError("Missing required parameter: a")
        if b is None:
            raise WorkflowValidationError("Missing required parameter: b")
        result = a + b
    except Exception as exc:
        raise WorkflowValidationError(f"Failed to add numbers: {exc}") from exc
    return f"The sum of {a} and {b} is {result}."
