from agent.executor.dynamic_workflow import WorkflowGenerationManager


def test_dynamic_generation_requires_api_key():
    manager = WorkflowGenerationManager()
    manager.generator.api_key = None  # simulate missing configuration
    outcome = manager.ensure_workflow("demo:newfeature", extras={})
    assert not outcome.success
    assert outcome.errors
