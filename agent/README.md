# Agent Core (`agent/`)

This directory contains the Python backend for CloneAI. It is structured into two main components: **Core** (the brain) and **Skills** (the capabilities).

## Directory Structure

| Directory | Description |
|PO|---|
| `core/` | **The Brain**. Contains the fundamental logic for planning, LLM communication, and memory. |
| `skills/` | **The Hands**. Modular capabilities like Email, Calendar, etc. Each skill is self-contained. |
| `server/` | **The Interface**. A FastAPI server that exposes the agent's capabilities to the Electron frontend. |
| `tools/` | **Legacy Tools**. Older tool implementations being migrated to `skills/`. |
| `workflows/` | **Registry**. Manages the registration and discovery of available workflows. |
| `executor/` | **Execution Engine**. Handles the actual running of workflows and commands. |

## Key Files

*   `cli.py`: The command-line interface entry point.
*   `system_info.py`: Utilities for retrieving system information.
*   `system_artifacts.py`: Manages generated files (artifacts) like images or documents.

## Development Guide

If you are adding a new feature:
1.  **New Capability**: Create a new folder in `skills/` (e.g., `skills/spotify`).
2.  **Core Logic Change**: Modify `core/`.
3.  **API Change**: Update `server/api.py`.
