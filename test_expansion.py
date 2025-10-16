#!/usr/bin/env python3
"""
Quick test for dynamic step expansion feature.
"""

from agent.tools.tiered_planner import (
    classify_request,
    plan_step_execution,
    WorkflowMemory
)

def test_classification():
    """Test that classification properly breaks down numbered requests."""
    print("=" * 60)
    print("TEST 1: Classification should break 'reply to 5 emails' into 6 steps")
    print("=" * 60)
    
    result = classify_request("reply to my last 5 emails")
    
    print(f"\nAction Type: {result.can_handle_locally}")
    print(f"Categories: {result.categories}")
    print(f"Needs Sequential: {result.needs_sequential}")
    print(f"\nSteps Plan ({len(result.steps_plan)} steps):")
    for i, step in enumerate(result.steps_plan, 1):
        print(f"  {i}. {step}")
    
    print(f"\nReasoning: {result.reasoning}")
    
    # Check if we got proper breakdown
    if len(result.steps_plan) >= 5:
        print("\n✅ PASS: Got 5+ steps (proper breakdown)")
    else:
        print(f"\n❌ FAIL: Only got {len(result.steps_plan)} steps (should be 6: retrieve + 5 replies)")


def test_expansion():
    """Test that step execution can dynamically expand steps."""
    print("\n" + "=" * 60)
    print("TEST 2: Step execution should expand broad steps")
    print("=" * 60)
    
    # Create mock memory with context
    memory = WorkflowMemory(
        original_request="reply to my last 5 emails",
        steps_plan=["Retrieve last 5 emails", "Reply to each email"],
        categories=["mail"],
        context={
            "mail:last_message_ids": ["MSG001", "MSG002", "MSG003", "MSG004", "MSG005"]
        }
    )
    
    # Simulate having executed step 1
    memory.add_step("Retrieve last 5 emails", "mail:last count:5", 
                   "Retrieved 5 message IDs")
    
    # Now plan step 2 (the broad "Reply to each email" step)
    plan = plan_step_execution(
        current_step_instruction="Reply to each email",
        memory=memory,
        categories=["mail"]
    )
    
    print(f"\nExecution Plan:")
    print(f"  Can Execute: {plan.can_execute}")
    print(f"  Needs Expansion: {plan.needs_expansion}")
    print(f"  Reasoning: {plan.reasoning}")
    
    if plan.needs_expansion:
        print(f"\n  Expanded Steps ({len(plan.expanded_steps)}):")
        for i, step in enumerate(plan.expanded_steps, 1):
            print(f"    {i}. {step}")
        
        if len(plan.expanded_steps) == 5:
            print("\n✅ PASS: Expanded into 5 reply steps")
        else:
            print(f"\n⚠️  WARNING: Got {len(plan.expanded_steps)} steps, expected 5")
    else:
        print("\n❌ FAIL: Step was not expanded")


if __name__ == "__main__":
    test_classification()
    test_expansion()
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
