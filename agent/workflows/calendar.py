"""Calendar-related workflows registered with the workflow registry."""

from __future__ import annotations

from typing import Any, Dict

from agent.tools.calendar import create_calendar_event, list_calendar_events
from agent.workflows import ParameterSpec, WorkflowContext, WorkflowValidationError, register_workflow


@register_workflow(
    namespace="calendar",
    name="create",
    summary="Create calendar event",
    description="Creates a new calendar event with specified details.",
    parameters=(
        ParameterSpec(
            name="title",
            description="Event title",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="start",
            description="Start time (YYYY-MM-DDTHH:MM:SS)",
            type=str,
            required=True,
        ),
        ParameterSpec(
            name="end",
            description="End time (YYYY-MM-DDTHH:MM:SS)",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="duration",
            description="Duration in minutes (alternative to end time)",
            type=int,
            default=None,
        ),
        ParameterSpec(
            name="location",
            description="Event location",
            type=str,
            default=None,
        ),
        ParameterSpec(
            name="description",
            description="Event description",
            type=str,
            default=None,
        ),
    ),
    metadata={
        "category": "CALENDAR COMMANDS",
        "usage": "calendar:create title:TEXT start:DATETIME [end:DATETIME|duration:MINS] [location:TEXT] [description:TEXT]",
        "returns": "str",
        "examples": [
            "calendar:create title:Team Meeting start:2025-10-15T14:00:00 duration:60",
            "calendar:create title:Lunch start:2025-10-15T12:00:00 end:2025-10-15T13:00:00 location:Restaurant"
        ],
    },
)
def calendar_create_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for creating calendar events."""
    title = params.get("title")
    start = params.get("start")
    end = params.get("end")
    duration = params.get("duration")
    location = params.get("location")
    description = params.get("description")
    
    if not title or not start:
        raise WorkflowValidationError("'title' and 'start' are required")
    
    return create_calendar_event(
        summary=title,
        start_time=start,
        end_time=end,
        duration_minutes=duration if duration else 60,
        location=location,
        description=description
    )


@register_workflow(
    namespace="calendar",
    name="list",
    summary="List upcoming events",
    description="Lists upcoming calendar events.",
    parameters=(
        ParameterSpec(
            name="next",
            description="Number of upcoming events to list",
            type=int,
            default=5,
            aliases=["count", "max"]
        ),
    ),
    metadata={
        "category": "CALENDAR COMMANDS",
        "usage": "calendar:list [next N]",
        "returns": "str",
        "examples": [
            "calendar:list",
            "calendar:list next 10"
        ],
    },
)
def calendar_list_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    """Workflow handler for listing calendar events."""
    count = params.get("next", 5)
    return list_calendar_events(count)
