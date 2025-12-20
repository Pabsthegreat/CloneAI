# Planners (`agent/core/planning/`)

This module contains the algorithms that decide *what* to do.

## Key Files

*   `tiered.py`: **Tiered Planner**. The main planner. It uses a two-step process:
    1.  **Classification**: Determines if the request is a simple chat, a single command, or a multi-step workflow.
    2.  **Planning**: Generates a sequence of steps to fulfill the request.
*   `sequential.py`: **Sequential Planner**. A simpler planner that executes steps one after another (legacy/fallback).

## How it works

The `tiered.py` planner is the entry point for most user requests. It maintains a `WorkflowMemory` to track the state of multi-step tasks.
