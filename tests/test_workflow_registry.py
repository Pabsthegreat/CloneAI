import pytest

from agent.workflows import (
    ParameterSpec,
    WorkflowExecutionResult,
    WorkflowRegistry,
    WorkflowValidationError,
    build_command_reference,
    load_builtin_workflows,
    registry as global_registry,
)


def test_custom_registry_parses_arguments():
    """Ensure the default parser handles key/value arguments."""
    registry = WorkflowRegistry()

    @registry.register_decorator(
        namespace="demo",
        name="greet",
        summary="Say hello.",
        description="Simple greeting workflow.",
        parameters=(
            ParameterSpec(name="name", type=str, required=True),
            ParameterSpec(name="count", type=int, default=1),
        ),
    )
    def _handler(_ctx, params):
        return f"Hello {params['name']}" * params.get("count", 1)

    result = registry.execute("demo:greet name:World count:2")
    assert isinstance(result, WorkflowExecutionResult)
    assert result.arguments == {"name": "World", "count": 2}
    assert result.output == "Hello WorldHello World"

    with pytest.raises(WorkflowValidationError):
        registry.execute("demo:greet")


def test_mail_list_workflow_dispatch(monkeypatch):
    """mail:list should be handled by the workflow registry."""
    load_builtin_workflows()

    def fake_get_messages(count: int, sender: str | None = None, query: str | None = None):
        return [
            {
                "id": "abc123",
                "from": sender or "boss@example.com",
                "subject": "Subject",
                "date": "2025-01-01",
                "snippet": "Snippet",
            }
        ]

    monkeypatch.setattr("agent.skills.mail.workflows.get_email_messages", fake_get_messages)

    result = global_registry.execute("mail:list last 7 sender:boss@example.com")
    assert result.arguments["count"] == 7
    assert result.arguments["sender"] == "boss@example.com"
    assert "abc123" in result.output


def test_build_command_reference_includes_legacy_and_dynamic():
    """The command reference should reflect both registry entries and legacy commands."""
    reference_text = build_command_reference()
    assert "mail:list [last" in reference_text
    # Legacy entries should still be listed.
    assert "mail:view id:MESSAGE_ID" in reference_text


def test_mail_list_fallback_to_partial_sender(monkeypatch):
    """get_email_messages should attempt partial sender matches when no exact hits."""
    from agent.tools import mail as mail_tools

    calls = []

    class FakeClient:
        def list_messages(self, *, max_results, sender=None, query=None):
            calls.append((sender, query))
            if query == "from:moneycontrol":
                return [{"id": "abc123"}]
            return []

    monkeypatch.setattr(mail_tools, "GmailClient", FakeClient)

    messages = mail_tools.get_email_messages(
        count=1,
        sender="moneycontrol@moneycontrol.com",
        query=None,
    )

    assert messages == [{"id": "abc123"}]
    assert ("moneycontrol@moneycontrol.com", None) in calls
    assert (None, "from:moneycontrol") in calls
