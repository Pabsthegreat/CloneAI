"""Scheduler-related workflows registered with the workflow registry."""

from __future__ import annotations

from typing import Any, Dict

from agent.tools.scheduler import list_scheduled_tasks, add_scheduled_task, remove_scheduled_task, toggle_scheduled_task
from agent.workflows import ParameterSpec, WorkflowContext, WorkflowValidationError, register_workflow


@register_workflow(
    namespace="tasks",
    name="list",
    summary="List all scheduled tasks",
    description="Lists all scheduled tasks in the system.",
    parameters=(),
    metadata={
        "category": "SCHEDULER COMMANDS",
        "usage": "tasks",
        "returns": "str",
        "examples": ["tasks"],
    },
)
def tasks_list_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing scheduled tasks."""
    return list_scheduled_tasks()


@register_workflow(
    namespace="task",
    name="add",
    summary="Add scheduled task",
    description="Adds a new scheduled task to run at a specific time.",
    parameters=(
        ParameterSpec(
            name="name",
            description="Task name/description",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="command",
            description="Command to execute",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="time",
            description="Time to run (HH:MM in 24-hour format)",
            type=str,
            required=True,
        ),
    ),
    metadata={
        "category": "SCHEDULER COMMANDS",
        "usage": "task:add name:TEXT command:COMMAND time:HH:MM",
        "returns": "str",
        "examples": [
            "task:add name:Morning Email command:mail:list time:09:00",
            "task:add name:Daily Backup command:backup.sh time:23:00"
        ],
    },
)
def task_add_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for adding scheduled tasks."""
    name = params.get("name")
    command = params.get("command")
    time = params.get("time")
    
    if not name or not command or not time:
        raise WorkflowValidationError("'name', 'command', and 'time' are required")
    
    return add_scheduled_task(name, command, time)


@register_workflow(
    namespace="task",
    name="remove",
    summary="Remove scheduled task",
    description="Removes a scheduled task by ID.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Task ID to remove",
            type=str,
            required=True,
            aliases=["task_id"]
        ),
    ),
    metadata={
        "category": "SCHEDULER COMMANDS",
        "usage": "task:remove TASK_ID",
        "returns": "str",
        "examples": ["task:remove task_123"],
    },
)
def task_remove_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for removing scheduled tasks."""
    task_id = params.get("id")
    
    if not task_id:
        raise WorkflowValidationError("'id' is required")
    
    return remove_scheduled_task(task_id)


@register_workflow(
    namespace="task",
    name="toggle",
    summary="Enable/disable scheduled task",
    description="Toggles a scheduled task between enabled and disabled states.",
    parameters=(
        ParameterSpec(
            name="id",
            description="Task ID to toggle",
            type=str,
            required=True,
            aliases=["task_id"]
        ),
    ),
    metadata={
        "category": "SCHEDULER COMMANDS",
        "usage": "task:toggle TASK_ID",
        "returns": "str",
        "examples": ["task:toggle task_123"],
    },
)
def task_toggle_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for toggling scheduled tasks."""
    task_id = params.get("id")
    
    if not task_id:
        raise WorkflowValidationError("'id' is required")
    
    return toggle_scheduled_task(task_id)
