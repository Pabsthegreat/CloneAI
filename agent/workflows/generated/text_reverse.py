from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext, WorkflowValidationError
from typing import Dict, Any

@register_workflow(
    namespace="text",
    name="reverse",
    summary="Auto-generated workflow for `text:reverse`",
    description="Implements the CLI command `text:reverse input:Hello`.",
    parameters=(
        ParameterSpec(
            name="input",
            description="The text to reverse.",
            type=str,
            required=True,
            position=0,
        ),
    ),
)
def text_reverse_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    input_text = params.get("input")
    if input_text is None:
        raise WorkflowValidationError("Missing required parameter: input")
    if not isinstance(input_text, str):
        raise WorkflowValidationError("Parameter 'input' must be a string.")
    try:
        reversed_text = input_text[::-1]
    except Exception as exc:
        raise WorkflowValidationError(f"Failed to reverse text: {exc}")
    return reversed_text
