# Workflow Registry (`agent/workflows/`)

This module manages the registration and discovery of agent capabilities.

## Key Files

*   `registry.py`: **The Registry**. A singleton that stores all available workflows (commands).
*   `__init__.py`: **Loader**. Automatically discovers and imports workflow modules from `agent/skills/` and `agent/workflows/`.

## How Registration Works

Workflows are registered using the `@register_workflow` decorator:

```python
@register_workflow(
    namespace="my_skill",
    action="do_something",
    description="Does something cool"
)
def my_function(param1: str):
    ...
```
