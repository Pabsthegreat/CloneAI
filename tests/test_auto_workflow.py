from typer.testing import CliRunner

import agent.cli as cli


def test_auto_executes_parsed_steps(monkeypatch):
    runner = CliRunner()

    executed_commands = []

    def fake_execute(command: str, *, extras=None) -> str:
        executed_commands.append(command)
        if extras is not None and command.startswith("mail:list"):
            extras["mail:last_message_ids"] = ["abc123"]
        return f"Executed {command}"

    def fake_parse_workflow(_instruction: str):
        return {
            "success": True,
            "steps": [
                {
                    "command": "mail:draft to:test@example.com subject:Hi body:Hello",
                    "description": "Create a draft email",
                    "needs_approval": False,
                }
            ],
            "reasoning": "Draft email as requested.",
        }

    # Prevent file writes during tests
    monkeypatch.setattr(cli, "log_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "execute_single_command", fake_execute)
    monkeypatch.setattr("agent.tools.nl_parser.parse_workflow", fake_parse_workflow)
    monkeypatch.setattr("typer.confirm", lambda *args, **kwargs: False)

    result = runner.invoke(cli.app, ["auto", "--run", "compose a draft email"])

    assert result.exit_code == 0
    assert executed_commands == [
        "mail:draft to:test@example.com subject:Hi body:Hello"
    ]
    assert "Executed mail:draft to:test@example.com subject:Hi body:Hello" in result.stdout
    assert "Automated Email Reply Workflow" not in result.stdout


def test_auto_resolves_message_id_placeholder(monkeypatch):
    runner = CliRunner()
    executed_commands = []

    def fake_execute(command: str, *, extras=None) -> str:
        executed_commands.append(command)
        if extras is not None and command.startswith("mail:list"):
            extras["mail:last_message_ids"] = ["xyz987"]
        return f"Executed {command}"

    def fake_parse_workflow(_instruction: str):
        return {
            "success": True,
            "steps": [
                {
                    "command": "mail:list last 1 sender:alerts@example.com",
                    "description": "List last alert email",
                    "needs_approval": False,
                },
                {
                    "command": "mail:view id:MESSAGE_ID",
                    "description": "View that email",
                    "needs_approval": False,
                },
            ],
            "reasoning": "Find and view the latest alert email.",
        }

    monkeypatch.setattr(cli, "log_command", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "execute_single_command", fake_execute)
    monkeypatch.setattr("agent.tools.nl_parser.parse_workflow", fake_parse_workflow)

    result = runner.invoke(cli.app, ["auto", "--run", "read the latest alert email"])

    assert result.exit_code == 0
    assert executed_commands == [
        "mail:list last 1 sender:alerts@example.com",
        "mail:view id:xyz987",
    ]
    assert "mail:view id:xyz987" in result.stdout
