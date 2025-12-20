# LLM Clients (`agent/core/llm/`)

This module handles all interactions with Large Language Models.

## Key Files

*   `ollama.py`: Client for interacting with local Ollama models. Handles context window management and JSON parsing.

## Usage

```python
from agent.core.llm.ollama import run_ollama

response = run_ollama(
    prompt="Hello, world!",
    model="llama3",
    format="json"  # Optional: force JSON output
)
```
