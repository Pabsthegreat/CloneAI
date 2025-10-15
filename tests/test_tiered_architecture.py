"""
Test the tiered architecture implementation.

Run with:
    python -m pytest tests/test_tiered_architecture.py -v
"""

import pytest
from agent.tools.tiered_planner import (
    classify_request,
    plan_step_execution,
    WorkflowMemory,
    ClassificationResult,
    StepExecutionPlan,
)


def test_workflow_memory():
    """Test memory initialization and operations."""
    memory = WorkflowMemory(
        original_request="test request",
        steps_plan=["step 1", "step 2", "step 3"],
        categories=["mail"]
    )
    
    assert memory.get_current_step_number() == 1
    assert not memory.is_complete()
    assert len(memory.get_remaining_steps()) == 3
    
    # Add a completed step
    memory.add_step("step 1", "mail:list", "output 1")
    
    assert memory.get_current_step_number() == 2
    assert not memory.is_complete()
    assert len(memory.get_remaining_steps()) == 2
    assert len(memory.completed_steps) == 1
    
    # Complete all steps
    memory.add_step("step 2", "mail:view id:1", "output 2")
    memory.add_step("step 3", "mail:reply id:1", "output 3")
    
    assert memory.is_complete()
    assert len(memory.completed_steps) == 3
    
    # Test summary generation
    summary = memory.get_summary()
    assert "Original Request:" in summary
    assert "step 1" in summary
    assert "mail:list" in summary


def test_memory_context():
    """Test memory context management."""
    memory = WorkflowMemory(
        original_request="test",
        steps_plan=["step 1"],
        categories=["mail"]
    )
    
    # Add context
    memory.context["mail:last_message_ids"] = ["MSG1", "MSG2", "MSG3"]
    memory.context["custom_data"] = "test value"
    
    summary = memory.get_summary()
    assert "mail:last_message_ids: 3 items" in summary
    assert "custom_data:" in summary


def test_classification_result():
    """Test classification result structure."""
    # Local answer
    result = ClassificationResult(
        can_handle_locally=True,
        local_answer="The answer is 42",
        categories=[],
        needs_sequential=False,
        steps_plan=[],
        reasoning="Simple math"
    )
    
    assert result.can_handle_locally
    assert result.local_answer == "The answer is 42"
    assert len(result.categories) == 0
    
    # Workflow execution
    result = ClassificationResult(
        can_handle_locally=False,
        categories=["mail", "calendar"],
        needs_sequential=True,
        steps_plan=["step 1", "step 2"],
        reasoning="Multi-step workflow"
    )
    
    assert not result.can_handle_locally
    assert "mail" in result.categories
    assert result.needs_sequential
    assert len(result.steps_plan) == 2


def test_step_execution_plan():
    """Test step execution plan structure."""
    # Execute command
    plan = StepExecutionPlan(
        can_execute=True,
        command="mail:list last 5",
        needs_new_workflow=False,
        reasoning="Use existing mail:list command"
    )
    
    assert plan.can_execute
    assert plan.command == "mail:list last 5"
    assert not plan.needs_new_workflow
    
    # Need new workflow
    plan = StepExecutionPlan(
        can_execute=False,
        needs_new_workflow=True,
        workflow_request={
            "namespace": "mail",
            "action": "check-urgency",
            "description": "Check email urgency"
        },
        reasoning="No existing workflow for urgency check"
    )
    
    assert not plan.can_execute
    assert plan.needs_new_workflow
    assert plan.workflow_request["namespace"] == "mail"
    
    # Local answer
    plan = StepExecutionPlan(
        can_execute=True,
        local_answer="The result is 25",
        reasoning="Simple calculation"
    )
    
    assert plan.can_execute
    assert plan.local_answer == "The result is 25"


def test_memory_summary_formatting():
    """Test that memory summary is well-formatted."""
    memory = WorkflowMemory(
        original_request="check emails and reply",
        steps_plan=[
            "List recent emails",
            "Identify urgent emails",
            "Reply to urgent ones"
        ],
        categories=["mail"]
    )
    
    # Add some completed steps
    memory.add_step(
        "List recent emails",
        "mail:list last 10",
        "Found 10 emails with IDs: MSG1, MSG2, MSG3..."
    )
    
    memory.context["mail:last_message_ids"] = ["MSG1", "MSG2", "MSG3"]
    
    summary = memory.get_summary()
    
    # Verify structure
    assert "Original Request: check emails and reply" in summary
    assert "Plan (3 steps):" in summary
    assert "✓ 1. List recent emails" in summary
    assert "○ 2. Identify urgent emails" in summary
    assert "Completed Steps:" in summary
    assert "Command: mail:list last 10" in summary
    assert "Available Context:" in summary
    assert "mail:last_message_ids: 3 items" in summary


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])
