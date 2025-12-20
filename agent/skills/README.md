# Skills (`agent/skills/`)

This directory contains the modular capabilities of the agent. Each subdirectory represents a specific domain or "skill".

## Structure of a Skill

Each skill folder (e.g., `mail/`) should ideally contain:

*   `client.py`: The low-level logic and API clients (e.g., Gmail API wrapper).
*   `workflows.py`: The high-level command definitions registered with the agent.
*   `__init__.py`: Exports relevant classes.

## Available Skills

*   `mail/`: Email management (Gmail).
*   *(More to come: Calendar, Web Search, etc.)*

## Adding a New Skill

1.  Create a folder: `agent/skills/my_skill/`
2.  Add `client.py` for logic.
3.  Add `workflows.py` and use `@register_workflow` to expose commands.
4.  The agent will automatically discover it on startup.
