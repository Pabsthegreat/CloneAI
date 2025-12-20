# API Server (`agent/server/`)

This directory contains the FastAPI server that powers the Electron Desktop App.

## Key Files

*   `api.py`: **Main Entry Point**. Defines all REST endpoints (`/api/chat`, `/api/health`, etc.).

## Architecture

The server acts as a bridge between the Electron frontend and the Python `agent` core.
*   **Chat Endpoint** (`POST /api/chat`): Receives user messages, passes them to the `TieredPlanner`, and returns the result.
*   **State**: It maintains some in-memory state (like email drafts) but mostly relies on the stateless agent logic.

## Running the Server

The server is typically started automatically by the Electron app. To run it manually:

```bash
python -m agent.server.api
```
