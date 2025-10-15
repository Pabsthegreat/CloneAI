import os
import re
import typer
from typing import Any, Dict, List, Optional
from agent.state import log_command, get_history, search_history, format_history_list, get_logger
from agent.system_info import print_system_info
from agent.workflows import (
    WorkflowExecutionError,
    WorkflowNotFoundError,
    WorkflowValidationError,
    load_builtin_workflows,
    registry as workflow_registry,
)
from agent.config.runtime import (
    LEGACY_COMMAND_PREFIXES,
    SEND_CONFIRMATION_KEYWORDS,
)

app = typer.Typer(help="Your personal CLI agent", no_args_is_help=True)

# Ensure built-in workflows are registered before commands execute.
load_builtin_workflows()

@app.callback()
def show_system_info(ctx: typer.Context):
    """Print system info before each command."""
    # Always show system info when a command is executed
    if ctx.invoked_subcommand:
        print_system_info()

@app.command()
def hi():
    """Say hello and prompt for user input."""
    typer.echo("👋 Hello! I'm your CloneAI assistant.")
    typer.echo("")
    
    # Prompt user for what they want to do
    user_input = typer.prompt("What would you like to do?")
    
    # Process the user's request
    typer.echo("")
    typer.secho(f"You said: {user_input}", fg=typer.colors.GREEN)
    typer.echo("")
    typer.echo("🤖 Processing your request...")
    
    # TODO: Add your actual processing logic here
    # For now, just acknowledge the input
    output = f"I understand you want to: {user_input}\n(This is where your agent logic will go)"
    typer.echo(output)
    
    # Log the interaction
    log_command(
        command=f"hi: {user_input}",
        output=output,
        command_type="hi",
        metadata={"user_input": user_input}
    )

@app.command()
def chat(message: str = typer.Argument(None, help="Your message to the agent")):
    """Chat with the AI agent."""
    if not message:
        message = typer.prompt("What would you like to do?")
    
    typer.echo("")
    typer.secho(f"You: {message}", fg=typer.colors.CYAN)
    typer.echo("")
    typer.echo("🤖 AI: Processing your request...")
    output = f"I understand you want to: {message}\n(Agent logic will be implemented here)"
    typer.echo(output)
    
    # Log the interaction
    log_command(
        command=f"chat: {message}",
        output=output,
        command_type="chat",
        metadata={"message": message}
    )

@app.command()
def do(action: str = typer.Argument(..., help="Action to perform")):
    """
    Execute actions with the AI agent. Supports cascading commands with '&&'.
    
    Examples:
        # Email - List & View
        clai do "mail:list last 5"
        clai do "mail:view id:MSG_ID"                 - View full email
        clai do "mail:download id:MSG_ID"             - Download attachments
        clai do "mail:priority last 10"               - View priority emails
        
        # Email - Meetings
        clai do "mail:scan-meetings"                  - Scan for meeting invites
        clai do "mail:add-meeting email-id:MSG_ID"    - Add meeting to calendar
        clai do "mail:invite to:user@test.com subject:Sync time:2025-10-15T14:00:00 duration:30"
        
        # Email - Priority Management
        clai do "mail:priority-add user@test.com"
        clai do "mail:priority-add @company.com"
        clai do "mail:priority-list"
        clai do "mail:priority-remove user@test.com"
        
        # Calendar
        clai do "calendar:create title:Meeting start:2025-10-15T14:00:00 duration:30"
        clai do "calendar:list next 5"
        
        # Scheduler
        clai do "tasks"                               - List scheduled tasks
        clai do "task:add name:Check Email command:mail:list time:12:00"
        clai do "task:remove 1"                       - Remove task by ID
        clai do "task:toggle 1"                       - Enable/disable task
        
        # Cascading Commands
        clai do "mail:scan-meetings && mail:priority last 5"
    """
    typer.echo("")
    typer.secho(f"🤖 Executing: {action}", fg=typer.colors.YELLOW)
    typer.echo("")
    
    # Handle cascading commands (&&)
    if '&&' in action:
        commands = [cmd.strip() for cmd in action.split('&&')]
        typer.secho(f"📋 Executing {len(commands)} cascading commands...", fg=typer.colors.CYAN)
        typer.echo("")
        
        results = []
        for i, cmd in enumerate(commands, 1):
            typer.secho(f"[{i}/{len(commands)}] {cmd}", fg=typer.colors.BLUE)
            result = execute_single_command(cmd)
            results.append(result)
            typer.echo(result)
            typer.echo("")
        
        # Log cascaded command
        log_command(
            command=f"do {action}",
            output=f"Executed {len(commands)} commands",
            command_type="cascade",
            metadata={"commands": commands, "count": len(commands)}
        )
        return
    
    # Execute single command
    result = execute_single_command(action)
    typer.echo(result)
    

def execute_single_command(action: str, *, extras: Optional[Dict[str, Any]] = None) -> str:
    """Execute a single command and return result."""

    if extras is None:
        registry_extras: Dict[str, Any] = {}
    else:
        registry_extras = extras
    if "logger" not in registry_extras:
        registry_extras["logger"] = get_logger()
    
    base_command = action.split()[0] if ' ' in action else action
    
    try:
        workflow_result = workflow_registry.execute(action, extras=registry_extras)
        output = workflow_result.output
        if not isinstance(output, str):
            output = str(output)

        metadata = {
            "workflow": registry_extras.get(
                "workflow", workflow_result.spec.command_key()
            ),
            "namespace": workflow_result.spec.namespace,
            "arguments": workflow_result.arguments,
            "source": "workflow_registry",
        }
        parameters_meta = registry_extras.get("parameters")
        if parameters_meta:
            metadata["parameters"] = parameters_meta

        if workflow_result.spec.metadata:
            metadata["workflow_metadata"] = dict(workflow_result.spec.metadata)

        log_command(
            command=f"do {action}",
            output=output,
            command_type=workflow_result.spec.namespace,
            metadata=metadata,
        )
        return output
    except WorkflowNotFoundError:
        is_legacy = any(base_command.startswith(prefix) for prefix in LEGACY_COMMAND_PREFIXES)
        generation_result = None
        if not is_legacy:
            from agent.executor.dynamic_workflow import dynamic_manager

            generation_result = dynamic_manager.ensure_workflow(action, extras=registry_extras)
            if generation_result.success and generation_result.output is not None:
                metadata = {
                    "workflow": f"{generation_result.spec_namespace}:{generation_result.spec_name}"
                    if generation_result.spec_namespace and generation_result.spec_name
                    else action,
                    "namespace": generation_result.spec_namespace or "generated",
                    "arguments": generation_result.arguments or {},
                    "source": "workflow_generator",
                }
                if generation_result.notes:
                    metadata["notes"] = generation_result.notes
                if generation_result.summary:
                    metadata["summary"] = generation_result.summary

                log_command(
                    command=f"do {action}",
                    output=generation_result.output,
                    command_type=metadata["namespace"],
                    metadata=metadata,
                )
                return generation_result.output

        if generation_result and generation_result.errors:
            typer.secho("❌ Workflow generation failed:", fg=typer.colors.RED)
            for err in generation_result.errors[-2:]:
                typer.echo(f"   • {err}")
        elif generation_result and not generation_result.success:
            typer.secho("❌ Unable to generate workflow automatically.", fg=typer.colors.RED)
    except (WorkflowValidationError, WorkflowExecutionError) as workflow_error:
        header = action.strip().split(" ", 1)[0] if action else ""
        namespace, _, _ = header.partition(":")
        error_metadata = {
            "workflow": header if ":" in header else None,
            "error": True,
            "detail": str(workflow_error),
            "source": "workflow_registry",
        }
        command_type = namespace or "workflow"
        log_command(
            command=f"do {action}",
            output=f"❌ {workflow_error}",
            command_type=command_type,
            metadata=error_metadata,
        )
        return f"❌ {workflow_error}"
    
    # If we reach here, workflow not found and couldn't be generated
    error_msg = f"❌ Unknown command: {action}"
    help_text = """

Available commands (use 'clai do "COMMAND"'):
  
  📧 Mail Commands:
    mail:list [last N]                    - List emails
    mail:view id:MSG_ID                   - View email
    mail:download id:MSG_ID               - Download attachments
    mail:draft to:EMAIL subject:TEXT      - Create draft
    mail:reply id:MSG_ID                  - Reply to email
    mail:send to:EMAIL subject:TEXT       - Send email
    mail:priority [last N]                - Priority inbox
    mail:scan-meetings                    - Scan for meetings
    
  📅 Calendar Commands:
    calendar:create title:X start:Y       - Create event
    calendar:list [next N]                - List events
    
  ⏰ Scheduler Commands:
    tasks:list                            - List tasks
    task:add name:X command:Y time:Z      - Add task
    task:remove ID                        - Remove task
    task:toggle ID                        - Toggle task
    
  📄 Document Commands:
    doc:merge-pdf files:X,Y output:Z      - Merge PDFs
    convert:pdf-to-docx input:FILE        - Convert to Word
    
  💬 General Commands:
    system:hi                             - Interactive greeting
    system:chat "message"                 - Chat with AI
    system:history                        - Command history
    system:reauth                         - Re-authenticate
    
  🔗 Cascading:
    Use && to chain: "mail:list && mail:priority"

For natural language: clai auto "your instruction"
"""
    
    log_command(
        command=f"do {action}",
        output=error_msg,
        command_type="unknown",
        metadata={"action": action, "error": True}
    )
    return error_msg + help_text


@app.command()
def auto(
    instruction: str = typer.Argument(..., help="Natural language instruction for multi-step workflow"),
    run: bool = typer.Option(False, "--run", "-r", help="Auto-execute workflow without approval")
):
    """
    Execute multi-step workflows from natural language instructions.
    
    Examples:
        clai auto "check my last 5 emails and reply to them"
        clai auto "schedule a meeting tomorrow at 2pm and send invites to team@example.com"
        clai auto --run "check calendar for today and email me a summary"
    """
    try:
        from agent.tools.nl_parser import parse_workflow
        from agent.tools.local_compute import can_local_llm_handle
        
        typer.secho(f"\n🔄 Parsing workflow: '{instruction}'", fg=typer.colors.CYAN, bold=True)
        
        # PRIORITY 1: Try to map to existing workflows first
        result = parse_workflow(instruction)
        
        if not result["success"] or not result.get("steps"):
            # PRIORITY 2: Check if local LLM can handle without workflows
            typer.secho("\n🧠 No workflow found, checking if local LLM can handle...", fg=typer.colors.MAGENTA, dim=True)
            can_handle, local_result = can_local_llm_handle(instruction)
            if can_handle and local_result:
                typer.echo("")
                typer.secho("💡 Computed locally (no API calls needed):", fg=typer.colors.GREEN, bold=True)
                typer.echo(local_result)
                typer.echo("")
                return
            else:
                # PRIORITY 3: Workflow generation would go here (already handled by execute_single_command)
                typer.secho(f"❌ Failed to parse workflow: {result.get('error', 'Unknown error')}", fg=typer.colors.RED)
                return
        
        steps = result["steps"]
        reasoning = result.get("reasoning", "")
        
        # PRIORITY 2.5: If single-step workflow and command doesn't exist, try local LLM before GPT generation
        if len(steps) == 1:
            first_command = steps[0]["command"]
            # Quick check: if it's a simple operation that local LLM can handle, try that first
            typer.secho("\n🧠 Checking if local LLM can handle...", fg=typer.colors.MAGENTA, dim=True)
            can_handle, local_result = can_local_llm_handle(instruction)
            if can_handle and local_result:
                typer.echo("")
                typer.secho("💡 Computed locally (no API calls needed):", fg=typer.colors.GREEN, bold=True)
                typer.echo(local_result)
                typer.echo("")
                return
            typer.secho("   → Using workflow\n", fg=typer.colors.MAGENTA, dim=True)
        
        # Display workflow plan
        typer.echo("")
        typer.secho("📋 Workflow Plan:", fg=typer.colors.YELLOW, bold=True)
        typer.echo(f"   {reasoning}")
        typer.echo("")
        
        typer.secho(f"   {len(steps)} step(s) identified:", fg=typer.colors.BLUE)
        for i, step in enumerate(steps, 1):
            command = step.get("command", "")
            description = step.get("description", "")
            needs_approval = "⚠️  Needs approval" if step.get("needs_approval", False) else "✓ Auto-execute"
            
            typer.echo(f"\n   Step {i}: {description}")
            typer.echo(f"           Command: {command}")
            typer.echo(f"           {needs_approval}")
        
        # Check if we need sequential re-planning (has placeholders like MESSAGE_ID)
        has_placeholders = any("MESSAGE_ID" in step.get("command", "") or "DRAFT_ID" in step.get("command", "") 
                              for step in steps)
        
        if has_placeholders:
            typer.secho("\n💡 Detected dynamic workflow - will plan steps sequentially", fg=typer.colors.BLUE, dim=True)
        
        # Get approval unless --run flag is set
        if not run:
            typer.echo("")
            confirmation = typer.confirm("Do you want to execute this workflow?")
            if not confirmation:
                typer.secho("❌ Workflow cancelled by user", fg=typer.colors.YELLOW)
                return
        
        # Execute workflow steps
        typer.echo("")
        typer.secho("🚀 Executing workflow...", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        
        workflow_outputs = []
        auto_context: Dict[str, List[str]] = {}
        instruction_lower = instruction.lower()
        should_offer_send = any(keyword in instruction_lower for keyword in SEND_CONFIRMATION_KEYWORDS)
        completed_steps = []  # Track for sequential planning

        def resolve_placeholders(raw_command: str) -> str:
            resolved = raw_command
            message_ids = auto_context.get("mail:last_message_ids")
            if message_ids:
                resolved = resolved.replace("MESSAGE_ID", message_ids[0], 1)
            draft_ids = auto_context.get("mail:last_draft_ids")
            if draft_ids:
                resolved = resolved.replace("DRAFT_ID", draft_ids[0], 1)
            return resolved

        i = 0
        while i < len(steps):
            i += 1
            step = steps[i - 1]
            command = step.get("command", "").strip()
            description = step.get("description", "").strip() or command
            needs_approval = bool(step.get("needs_approval"))

            typer.secho(f"▶ Step {i}/{len(steps)}: {description}", fg=typer.colors.CYAN, bold=True)
            if not command:
                typer.secho("   ⚠️  Missing command for this step; skipping.", fg=typer.colors.YELLOW)
                typer.echo("")
                continue

            command_to_run = resolve_placeholders(command)
            if "MESSAGE_ID" in command_to_run or "DRAFT_ID" in command_to_run:
                typer.secho(
                    "   ⚠️  Placeholder in command could not be resolved; skipping.",
                    fg=typer.colors.YELLOW,
                )
                typer.echo("")
                continue

            typer.echo(f"   Executing: {command_to_run}")

            if needs_approval and not run:
                typer.echo("")
                proceed = typer.confirm(f"Execute this step now?", default=True)
                if not proceed:
                    typer.secho("   ⚠️  Step skipped by user.", fg=typer.colors.YELLOW)
                    typer.echo("")
                    continue

            step_extras: Dict[str, Any] = {}
            try:
                result = execute_single_command(command_to_run, extras=step_extras)
            except Exception as exc:  # pragma: no cover - defensive
                typer.secho(f"   ❌ Error executing command: {exc}", fg=typer.colors.RED)
                workflow_outputs.append(f"{command_to_run}\nERROR: {exc}")
                typer.echo("")
                continue

            # Update context from workflow extras
            if "mail:last_message_ids" in step_extras:
                auto_context["mail:last_message_ids"] = step_extras["mail:last_message_ids"]
            if "mail:last_messages" in step_extras:
                auto_context["mail:last_messages"] = step_extras["mail:last_messages"]

            workflow_outputs.append(f"{command_to_run}\n{result}")
            if result:
                typer.echo("")
                typer.echo(result)
            typer.echo("")
            
            # Track completed steps for sequential planning
            completed_steps.append({"command": command_to_run, "output": result or ""})
            
            # SEQUENTIAL RE-PLANNING: Only use for complex multi-step analysis workflows
            # For simple single-step workflows (like summarize), just resolve placeholders
            if has_placeholders and i < len(steps):
                # Check if next step has placeholder
                next_step = steps[i] if i < len(steps) else None
                if next_step and ("MESSAGE_ID" in next_step.get("command", "") or "DRAFT_ID" in next_step.get("command", "")):
                    next_command = next_step.get("command", "")
                    
                    # Only invoke sequential planner for complex workflows (multiple views, urgency analysis, etc.)
                    # For simple workflows, just resolve the placeholder
                    needs_planning = (
                        "urgent" in instruction.lower() or
                        "priority" in instruction.lower() or
                        len([s for s in steps if "mail:view" in s.get("command", "")]) > 1
                    )
                    
                    if needs_planning:
                        from agent.tools.sequential_planner import plan_next_step
                        
                        typer.secho("🔄 Planning next step based on output...", fg=typer.colors.MAGENTA, dim=True)
                        
                        remaining_goal = reasoning  # Use original reasoning as goal
                        planned_step = plan_next_step(
                            instruction,
                            completed_steps,
                            remaining_goal,
                            context=auto_context,
                        )
                        
                        if planned_step and planned_step.get('has_next_step'):
                            # Replace the placeholder step with the dynamically planned one
                            steps[i] = {
                                "command": planned_step.get('command', ''),
                                "description": planned_step.get('description', ''),
                                "needs_approval": planned_step.get('needs_approval', False)
                            }
                            typer.secho(f"   → Next step: {planned_step.get('command', '')}\n", fg=typer.colors.MAGENTA, dim=True)
                        else:
                            # No more steps needed, truncate the workflow
                            steps = steps[:i]
                            typer.secho("   → No more steps needed\n", fg=typer.colors.MAGENTA, dim=True)
                    else:
                        # Simple workflow - just resolve placeholder without changing command
                        # The resolve_placeholders function will handle it in the next iteration
                        pass

            # Extract draft IDs from output when available
            if command_to_run.startswith("mail:draft"):
                draft_match = re.search(r"Draft ID:\s*([^\s]+)", result or "")
                if draft_match:
                    draft_id = draft_match.group(1)
                    auto_context["mail:last_draft_ids"] = [draft_id]

                    if should_offer_send:
                        typer.echo("")
                        send_now = typer.confirm("Do you want to send this draft now?", default=True)
                    else:
                        send_now = False

                    if send_now:
                        send_command = f"mail:send draft-id:{draft_id}"
                        typer.echo(f"   Executing: {send_command}")
                        send_extras: Dict[str, Any] = {}
                        try:
                            send_result = execute_single_command(send_command, extras=send_extras)
                            workflow_outputs.append(f"{send_command}\n{send_result}")
                            typer.echo(send_result)
                            auto_context["mail:last_sent_draft_id"] = [draft_id]
                        except Exception as send_exc:  # pragma: no cover
                            typer.secho(f"   ❌ Failed to send draft: {send_exc}", fg=typer.colors.RED)
                            workflow_outputs.append(f"{send_command}\nERROR: {send_exc}")
                        typer.echo("")
                    else:
                        typer.secho(
                            f"   ✅ Draft saved. Send later with: clai do \"mail:send draft-id:{draft_id}\"",
                            fg=typer.colors.GREEN,
                        )
                        typer.echo("")

        typer.secho("✅ Workflow completed!", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        typer.secho("💡 Tip: For full interactive control, use individual commands:", fg=typer.colors.BLUE)
        typer.echo("   • clai interpret \"your instruction\"")
        typer.echo("   • clai draft-email \"your message\"")
        typer.echo("   • clai do <command>")
        typer.echo("")

        log_command(
            command=f"auto {instruction}",
            output="\n\n".join(workflow_outputs),
            command_type="auto",
            metadata={
                "steps": steps,
                "run_flag": run,
                "reasoning": reasoning,
            },
        )
        
    except ImportError as e:
        typer.secho(f"❌ Import error: {str(e)}", fg=typer.colors.RED)
        typer.echo("Make sure agent.tools.nl_parser is available")
    except KeyboardInterrupt:
        typer.echo("")
        typer.secho("❌ Workflow cancelled by user", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"❌ Unexpected error: {str(e)}", fg=typer.colors.RED)
        import traceback
        traceback.print_exc()

@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of entries to show"),
    command_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by command type (hi, chat, mail, do)"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search in commands and outputs"),
    stats: bool = typer.Option(False, "--stats", help="Show statistics about command history")
):
    """
    View command history (last 100 commands stored).
    
    Examples:
        clai history                  - Show last 10 commands
        clai history -n 20            - Show last 20 commands
        clai history -t mail          - Show only mail commands
        clai history -s "gmail.com"   - Search for "gmail.com"
        clai history --stats          - Show usage statistics
    """
    typer.echo("")
    
    if stats:
        # Show statistics
        logger = get_logger()
        stats_data = logger.get_stats()
        
        typer.secho("📊 Command History Statistics", fg=typer.colors.CYAN, bold=True)
        typer.echo("=" * 80)
        typer.echo(f"Total commands logged: {stats_data['total_commands']}/{stats_data['max_entries']}")
        typer.echo(f"\nCommands by type:")
        for cmd_type, count in stats_data['command_types'].items():
            typer.echo(f"  {cmd_type}: {count}")
        
        if stats_data['oldest_entry']:
            typer.echo(f"\nOldest entry: {stats_data['oldest_entry']}")
        if stats_data['newest_entry']:
            typer.echo(f"Newest entry: {stats_data['newest_entry']}")
        
        typer.echo("=" * 80)
        return
    
    # Get history entries
    if search:
        entries = search_history(search)
        title = f"Search Results for '{search}'"
    else:
        entries = get_history(limit=limit, command_type=command_type)
        if command_type:
            title = f"Last {len(entries)} {command_type.upper()} Commands"
        else:
            title = f"Last {len(entries)} Commands"
    
    # Format and display
    output = format_history_list(entries, title)
    typer.echo(output)

@app.command()
def clear_history(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """Clear all command history."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to clear all command history?")
    
    if confirm:
        logger = get_logger()
        logger.clear_history()
        typer.secho("✅ Command history cleared!", fg=typer.colors.GREEN)
    else:
        typer.echo("Cancelled.")

@app.command()
def reload():
    """
    Reload CloneAI (re-source your shell profile).
    
    This is a helper command that reminds you how to reload your shell.
    """
    import platform
    from agent.system_info import get_shell_name
    
    shell = get_shell_name()
    system = platform.system()
    
    typer.echo("")
    typer.secho("🔄 To reload CloneAI, run:", fg=typer.colors.YELLOW)
    typer.echo("")
    
    if system == "Windows" or shell == "PowerShell":
        typer.secho("   . $PROFILE", fg=typer.colors.CYAN, bold=True)
    elif shell in ["Bash", "bash"]:
        typer.secho("   source ~/.bashrc", fg=typer.colors.CYAN, bold=True)
    elif shell in ["Zsh", "zsh"]:
        typer.secho("   source ~/.zshrc", fg=typer.colors.CYAN, bold=True)
    else:
        typer.secho("   source ~/.bashrc    # or ~/.zshrc", fg=typer.colors.CYAN, bold=True)
    
    typer.echo("")
    typer.echo("Or close and reopen your terminal.")
    typer.echo("")

@app.command()
def reauth(
    service: Optional[str] = typer.Argument(None, help="Service to re-authenticate (gmail, calendar, or all)")
):
    """
    Re-authenticate with Google APIs by deleting tokens and prompting for new authentication.
    
    Examples:
        clai reauth              - Re-auth all services (Gmail + Calendar)
        clai reauth gmail        - Re-auth Gmail only
        clai reauth calendar     - Re-auth Calendar only
    """
    import os
    from agent.system_info import get_gmail_token_path, get_calendar_token_path
    
    gmail_token = str(get_gmail_token_path())
    calendar_token = str(get_calendar_token_path())
    
    # Determine which tokens to delete
    if service is None or service.lower() == "all":
        tokens_to_delete = [
            ("Gmail", gmail_token),
            ("Calendar", calendar_token)
        ]
        service_name = "all services"
    elif service.lower() in ["gmail", "mail", "email"]:
        tokens_to_delete = [("Gmail", gmail_token)]
        service_name = "Gmail"
    elif service.lower() in ["calendar", "cal"]:
        tokens_to_delete = [("Calendar", calendar_token)]
        service_name = "Calendar"
    else:
        typer.secho(f"❌ Unknown service: {service}", fg=typer.colors.RED)
        typer.echo("Valid options: gmail, calendar, all")
        return
    
    typer.echo("")
    typer.secho(f"🔄 Re-authenticating {service_name}...", fg=typer.colors.YELLOW)
    typer.echo("")
    
    # Delete tokens
    deleted_count = 0
    for name, token_path in tokens_to_delete:
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
                typer.secho(f"✅ Deleted {name} token", fg=typer.colors.GREEN)
                deleted_count += 1
            except Exception as e:
                typer.secho(f"❌ Error deleting {name} token: {e}", fg=typer.colors.RED)
        else:
            typer.secho(f"ℹ️  {name} token not found (may not have been authenticated yet)", fg=typer.colors.BLUE)
    
    if deleted_count == 0:
        typer.echo("\nNo tokens were deleted. You may not have authenticated yet.")
        return
    
    # Provide next steps
    typer.echo("")
    typer.secho("✅ Tokens deleted successfully!", fg=typer.colors.GREEN)
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("1. Make sure you've added the required scopes in Google Cloud Console:")
    typer.echo("   - gmail.readonly")
    typer.echo("   - gmail.compose")
    typer.echo("   - gmail.send")
    typer.echo("   - calendar")
    typer.echo("")
    typer.echo("2. Run a command to trigger re-authentication:")
    
    if service_name in ["Gmail", "all services"]:
        typer.echo("   For Gmail: clai do \"mail:list last 5\"")
    if service_name in ["Calendar", "all services"]:
        typer.echo("   For Calendar: clai do \"calendar:list next 5\"")
    
    typer.echo("")
    typer.echo("Your browser will open to complete authentication.")
    typer.echo("")
    
    # Log the command
    log_command(
        command=f"reauth {service_name}",
        output=f"Deleted {deleted_count} token(s)",
        command_type="reauth",
        metadata={"service": service_name, "tokens_deleted": deleted_count}
    )

@app.command()
def merge(
    doc_type: str = typer.Argument(..., help="Document type: 'pdf' or 'ppt'")
):
    """
    Merge multiple PDF or PowerPoint files into one.
    
    Interactive command that asks for:
    - Directory containing files
    - File selection method (manual list, range, or all)
    - Output filename
    - Sort order (chronological or reverse)
    
    Examples:
        clai merge pdf
        clai merge ppt
    """
    from agent.tools.documents import list_documents_in_directory, merge_pdf_files, merge_ppt_files
    
    doc_type = doc_type.lower()
    if doc_type not in ['pdf', 'ppt']:
        typer.secho(f"❌ Invalid document type: {doc_type}", fg=typer.colors.RED)
        typer.echo("Valid options: pdf, ppt")
        return
    
    typer.echo("")
    typer.secho(f"📄 Merging {doc_type.upper()} files", fg=typer.colors.CYAN, bold=True)
    typer.echo("")
    
    # Get directory
    directory = typer.prompt("Enter directory path containing files")
    
    if not os.path.exists(directory):
        typer.secho(f"❌ Directory not found: {directory}", fg=typer.colors.RED)
        return
    
    # List available files
    try:
        files = list_documents_in_directory(directory, doc_type)
        if not files:
            typer.secho(f"❌ No {doc_type.upper()} files found in directory", fg=typer.colors.RED)
            return
        
        typer.echo("")
        typer.secho(f"Found {len(files)} {doc_type.upper()} file(s):", fg=typer.colors.GREEN)
        typer.echo("")
        
        # Sort by modification time for display
        files.sort(key=lambda x: x[1])
        for idx, (filename, mod_time) in enumerate(files, 1):
            typer.echo(f"{idx}. {filename} ({mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        typer.echo("")
        
    except Exception as e:
        typer.secho(f"❌ Error listing files: {str(e)}", fg=typer.colors.RED)
        return
    
    # Get merge method
    typer.echo("Select merge method:")
    typer.echo("1. Manual list (specify file numbers)")
    typer.echo("2. Range (start and end files)")
    typer.echo("3. All files in directory")
    typer.echo("")
    
    method = typer.prompt("Choose method [1/2/3]", type=int)
    
    file_list = None
    start_file = None
    end_file = None
    
    if method == 1:
        # Manual list
        typer.echo("")
        typer.echo("Enter file numbers to merge (comma-separated, e.g., 1,3,5):")
        indices = typer.prompt("File numbers")
        try:
            indices = [int(i.strip()) - 1 for i in indices.split(',')]
            file_list = [files[i][0] for i in indices if 0 <= i < len(files)]
            if not file_list:
                typer.secho("❌ Invalid file numbers", fg=typer.colors.RED)
                return
        except (ValueError, IndexError):
            typer.secho("❌ Invalid input", fg=typer.colors.RED)
            return
    
    elif method == 2:
        # Range
        typer.echo("")
        start_idx = typer.prompt("Enter start file number", type=int) - 1
        end_idx = typer.prompt("Enter end file number", type=int) - 1
        
        if 0 <= start_idx < len(files) and 0 <= end_idx < len(files):
            start_file = files[start_idx][0]
            end_file = files[end_idx][0]
        else:
            typer.secho("❌ Invalid file numbers", fg=typer.colors.RED)
            return
    
    elif method == 3:
        # All files
        pass
    else:
        typer.secho("❌ Invalid method", fg=typer.colors.RED)
        return
    
    # Get sort order
    typer.echo("")
    typer.echo("Sort order:")
    typer.echo("1. Chronological (oldest to newest)")
    typer.echo("2. Reverse chronological (newest to oldest)")
    order_choice = typer.prompt("Choose order [1/2]", type=int)
    order = 'asc' if order_choice == 1 else 'desc'
    
    # Get output filename
    typer.echo("")
    output_filename = typer.prompt(f"Enter output filename (without extension)")
    output_path = os.path.join(directory, f"{output_filename}.{doc_type}x" if doc_type == 'ppt' else f"{output_filename}.{doc_type}")
    
    # Perform merge
    typer.echo("")
    typer.secho(f"🔄 Merging {doc_type.upper()} files...", fg=typer.colors.YELLOW)
    
    try:
        if doc_type == 'pdf':
            result = merge_pdf_files(directory, output_path, file_list, start_file, end_file, order)
        else:
            result = merge_ppt_files(directory, output_path, file_list, start_file, end_file, order)
        
        typer.echo("")
        typer.secho(f"✅ Successfully merged {doc_type.upper()}!", fg=typer.colors.GREEN)
        typer.echo(f"Output: {result}")
        
        # Log command
        log_command(
            command=f"merge {doc_type}",
            output=f"Merged to {result}",
            command_type="merge",
            metadata={"doc_type": doc_type, "output": result}
        )
    
    except Exception as e:
        typer.echo("")
        typer.secho(f"❌ Error merging files: {str(e)}", fg=typer.colors.RED)

@app.command()
def scheduler(
    action: str = typer.Argument("start", help="Action: 'start' or 'status'")
):
    """
    Manage the task scheduler.
    
    Examples:
        clai scheduler start    - Start the scheduler daemon
        clai scheduler status   - Show scheduler status
    """
    if action == "start":
        from agent.tools.scheduler import start_scheduler
        
        typer.echo("")
        typer.secho("⏰ Starting CloneAI Scheduler...", fg=typer.colors.CYAN, bold=True)
        typer.echo("")
        
        try:
            # This will block and run the scheduler
            start_scheduler()
        except KeyboardInterrupt:
            typer.echo("")
            typer.secho("✅ Scheduler stopped", fg=typer.colors.GREEN)
        except Exception as e:
            typer.echo("")
            typer.secho(f"❌ Scheduler error: {str(e)}", fg=typer.colors.RED)
    
    elif action == "status":
        from agent.tools.scheduler import TaskScheduler
        
        try:
            scheduler = TaskScheduler()
            tasks = scheduler.get_tasks()
            enabled_tasks = scheduler.get_tasks(enabled_only=True)
            
            typer.echo("")
            typer.secho("⏰ Scheduler Status", fg=typer.colors.CYAN, bold=True)
            typer.echo("=" * 80)
            typer.echo(f"Total tasks: {len(tasks)}")
            typer.echo(f"Enabled tasks: {len(enabled_tasks)}")
            typer.echo(f"Disabled tasks: {len(tasks) - len(enabled_tasks)}")
            
            if enabled_tasks:
                typer.echo("\nEnabled tasks will run at:")
                for task in enabled_tasks:
                    typer.echo(f"  • {task['name']}: {task['time']} daily")
            
            typer.echo("\nRun 'clai do tasks' to see all scheduled tasks")
            typer.echo("Run 'clai scheduler start' to start the scheduler")
            typer.echo("=" * 80)
        except Exception as e:
            typer.secho(f"❌ Error: {str(e)}", fg=typer.colors.RED)
    
    else:
        typer.secho(f"❌ Unknown action: {action}", fg=typer.colors.RED)
        typer.echo("Valid actions: start, status")

@app.command()
def convert(
    conversion: str = typer.Argument(..., help="Conversion type: 'pdf-to-docx', 'docx-to-pdf', or 'ppt-to-pdf'")
):
    """
    Convert documents between formats.
    
    Supported conversions:
    - pdf-to-docx: Convert PDF to Word document
    - docx-to-pdf: Convert Word document to PDF (Windows only)
    - ppt-to-pdf: Convert PowerPoint to PDF (Windows only)
    
    Examples:
        clai convert pdf-to-docx
        clai convert docx-to-pdf
        clai convert ppt-to-pdf
    """
    from agent.tools.documents import convert_pdf_to_docx, convert_docx_to_pdf, convert_ppt_to_pdf
    import sys
    
    conversion = conversion.lower()
    valid_conversions = ['pdf-to-docx', 'docx-to-pdf', 'ppt-to-pdf']
    
    if conversion not in valid_conversions:
        typer.secho(f"❌ Invalid conversion: {conversion}", fg=typer.colors.RED)
        typer.echo(f"Valid options: {', '.join(valid_conversions)}")
        return
    
    # Check platform for Windows-only conversions
    if conversion in ['docx-to-pdf', 'ppt-to-pdf'] and sys.platform != 'win32':
        typer.secho(f"❌ {conversion} conversion is only supported on Windows", fg=typer.colors.RED)
        typer.echo("It requires Microsoft Office to be installed.")
        return
    
    typer.echo("")
    typer.secho(f"🔄 Converting: {conversion}", fg=typer.colors.CYAN, bold=True)
    typer.echo("")
    
    # Get input file
    input_file = typer.prompt("Enter input file path")
    
    if not os.path.exists(input_file):
        typer.secho(f"❌ File not found: {input_file}", fg=typer.colors.RED)
        return
    
    # Get output file
    default_output = os.path.splitext(input_file)[0]
    if conversion == 'pdf-to-docx':
        default_output += '.docx'
    elif conversion in ['docx-to-pdf', 'ppt-to-pdf']:
        default_output += '.pdf'
    
    output_file = typer.prompt("Enter output file path", default=default_output)
    
    # Perform conversion
    typer.echo("")
    typer.secho(f"🔄 Converting...", fg=typer.colors.YELLOW)
    
    try:
        if conversion == 'pdf-to-docx':
            result = convert_pdf_to_docx(input_file, output_file)
        elif conversion == 'docx-to-pdf':
            result = convert_docx_to_pdf(input_file, output_file)
        elif conversion == 'ppt-to-pdf':
            result = convert_ppt_to_pdf(input_file, output_file)
        
        typer.echo("")
        typer.secho("✅ Conversion successful!", fg=typer.colors.GREEN)
        typer.echo(f"Output: {result}")
        
        # Log command
        log_command(
            command=f"convert {conversion}",
            output=f"Converted to {result}",
            command_type="convert",
            metadata={"conversion": conversion, "input": input_file, "output": result}
        )
    
    except Exception as e:
        typer.echo("")
        typer.secho(f"❌ Conversion error: {str(e)}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
