# Core Logic (`agent/core/`)

This directory contains the fundamental "intelligence" of the agent. It is independent of specific tools or skills.

## Subdirectories

| Directory | Description |
|---|---|
| `llm/` | **LLM Clients**. Handles communication with AI models (Ollama, OpenAI, etc.). |
| `planning/` | **Planners**. Algorithms that break down user requests into executable steps. |
| `memory/` | **State**. (Planned) Management of conversation history and context. |

## Key Concepts

*   **Tiered Planning**: The agent uses a "Tiered" approach. It first classifies the intent, then plans the steps, then executes them.
*   **Model Agnostic**: The core is designed to work with local models (Ollama) or cloud models.
