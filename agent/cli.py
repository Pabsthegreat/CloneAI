import os
import re
import time
import typer
from typing import Any, Dict, List, Optional, Tuple
from agent.state import log_command, get_history, search_history, format_history_list, get_logger
from agent.system_info import print_system_info
from agent.system_artifacts import ArtifactsManager, resolve_file
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
from agent.tools.local_compute import can_local_llm_handle
from agent.config.autotune import apply_runtime_autotune
from agent.voice import get_voice_manager

app = typer.Typer(help="Your personal CLI agent", no_args_is_help=True)

# Initialize artifacts directories
ArtifactsManager.initialize()

# Apply system-based defaults for env vars, then ensure built-ins are registered.
try:
    apply_runtime_autotune()
except Exception:
    # Non-fatal if auto-tune fails; continue with defaults
    pass
load_builtin_workflows()

VOICE_MODE_ACTIVATE_PHRASES = (
    "activate voice mode",
    "start voice mode",
    "enable voice mode",
    "activate listening mode",
    "start listening mode",
    "enable listening mode",
    "turn on voice mode",
)

VOICE_MODE_DEACTIVATE_PHRASES = (
    "shutdown voice mode",
    "shut down voice mode",
    "stop voice mode",
    "disable voice mode",
    "deactivate voice mode",
    "turn off voice mode",
    "shutdown listening mode",
    "shut down listening mode",
    "stop listening mode",
    "disable listening mode",
    "deactivate listening mode",
)


def _detect_voice_mode_intent(instruction: str) -> Optional[str]:
    """Return 'activate' or 'deactivate' if the instruction targets voice mode."""
    normalized = instruction.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)

    if not normalized:
        return None

    for phrase in VOICE_MODE_DEACTIVATE_PHRASES:
        if phrase in normalized:
            return "deactivate"

    for phrase in VOICE_MODE_ACTIVATE_PHRASES:
        if phrase in normalized:
            return "activate"

    if "voice mode" in normalized or "listening mode" in normalized:
        if any(keyword in normalized for keyword in ("shutdown", "shut down", "stop", "disable", "deactivate", "turn off")):
            return "deactivate"
        if any(keyword in normalized for keyword in ("activate", "start", "enable", "turn on")):
            return "activate"

    return None


def _print_first_token_latency(start_time: float) -> None:
    elapsed = time.perf_counter() - start_time
    typer.secho(f"⏱️ First token latency: {elapsed:.2f}s", fg=typer.colors.MAGENTA, dim=True)


def _print_latency_breakdown(metrics: List[Tuple[str, float]]) -> None:
    if not metrics:
        return
    typer.secho("⏱️ Detailed stage breakdown:", fg=typer.colors.MAGENTA, dim=True)
    for label, elapsed in metrics:
        typer.echo(f"   • {label}: {elapsed:.2f}s")


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

    start_time = time.perf_counter()
    first_token_reported = False

    def report_latency_once():
        nonlocal first_token_reported
        if not first_token_reported:
            first_token_reported = True
            _print_first_token_latency(start_time)
    
    # Handle cascading commands (&&)
    if '&&' in action:
        commands = [cmd.strip() for cmd in action.split('&&')]
        typer.secho(f"📋 Executing {len(commands)} cascading commands...", fg=typer.colors.CYAN)
        typer.echo("")
        
        results = []
        for i, cmd in enumerate(commands, 1):
            typer.secho(f"[{i}/{len(commands)}] {cmd}", fg=typer.colors.BLUE)
            result = execute_single_command(cmd)
            report_latency_once()
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
    report_latency_once()
    typer.echo(result)
    

def execute_chained_commands(chained_action: str, *, extras: Optional[Dict[str, Any]] = None) -> str:
    """Execute multiple commands chained with && operator."""
    # Split by && and trim whitespace
    commands = [cmd.strip() for cmd in chained_action.split('&&')]
    
    results = []
    all_extras = extras or {}
    
    typer.secho(f"   🔗 Executing {len(commands)} chained commands...", fg=typer.colors.CYAN, dim=True)
    
    for i, cmd in enumerate(commands, 1):
        typer.echo(f"      {i}. {cmd}")
        try:
            # Execute each command individually, passing extras so context is shared
            result = execute_single_command_atomic(cmd, extras=all_extras)
            results.append(result)
            
            # Show brief success indicator
            if result:
                preview = result[:80].replace('\n', ' ')
                typer.secho(f"         ✓ {preview}...", fg=typer.colors.GREEN, dim=True)
        except Exception as exc:
            error_msg = f"Command {i} failed: {exc}"
            typer.secho(f"         ✗ {error_msg}", fg=typer.colors.RED)
            results.append(f"❌ {error_msg}")
            # Continue with remaining commands even if one fails
    
    # Combine all results
    combined = "\n\n".join(f"Command {i+1} result:\n{res}" for i, res in enumerate(results))
    return combined


def execute_single_command(action: str, *, extras: Optional[Dict[str, Any]] = None) -> str:
    """Execute a single command or chain of commands and return result."""
    
    # Check if this is a chained command (contains &&)
    if '&&' in action:
        return execute_chained_commands(action, extras=extras)
    
    return execute_single_command_atomic(action, extras=extras)


def execute_single_command_atomic(action: str, *, extras: Optional[Dict[str, Any]] = None) -> str:
    """Execute a single atomic command and return result."""

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
    Execute multi-step workflows using tiered architecture with memory.
    
    Architecture:
    0. GUARDRAIL: Check query safety (fast, lightweight check)
    1. PROMPT 1: Classify request → Get categories + planning strategy
    2. PROMPT 2+: Execute each step with memory → Get specific commands
    3. GPT Generation: Only called when LLM requests new workflow
    
    Examples:
        clai auto "check my last 5 emails and reply to urgent ones"
        clai auto "schedule a meeting tomorrow at 2pm and send invites"
        clai auto --run "check calendar for today and summarize"
    """
    start_time = time.perf_counter()
    first_token_reported = False

    def report_latency_once() -> None:
        nonlocal first_token_reported
        if not first_token_reported:
            first_token_reported = True
            _print_first_token_latency(start_time)

    start_time = time.perf_counter()
    first_token_reported = False

    def report_latency_once() -> None:
        nonlocal first_token_reported
        if not first_token_reported:
            first_token_reported = True
            _print_first_token_latency(start_time)

    voice_intent = _detect_voice_mode_intent(instruction)
    if voice_intent == "activate":
        typer.secho("\n🎙️  Activating conversational voice mode...", fg=typer.colors.CYAN, bold=True)
        manager = get_voice_manager()
        manager.activate()
        return
    if voice_intent == "deactivate":
        manager = get_voice_manager()
        if manager.is_active:
            typer.secho("\n🛑 Shutting down voice mode...", fg=typer.colors.YELLOW)
            manager.deactivate()
        else:
            typer.secho("\nℹ️  Voice mode is not currently active.", fg=typer.colors.BLUE)
        return

    latency_metrics: List[Tuple[str, float]] = []

    def record_latency(label: str, start_marker: float) -> None:
        latency_metrics.append((label, time.perf_counter() - start_marker))

    try:
        from agent.tools.tiered_planner import (
            classify_request,
            plan_step_execution,
            WorkflowMemory
        )
        from agent.tools.guardrails import check_query_safety, is_model_available
        
        typer.secho(f"\n🧠 Analyzing request (Tiered Architecture)...", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"   Request: '{instruction}'")
        typer.echo("")
        
        # ============================================================
        # GUARDRAIL: Safety Check (Optional - only if model available)
        # ============================================================
        # if is_model_available("qwen3:4b-instruct"):
        #     typer.secho("🛡️  Running safety check...", fg=typer.colors.YELLOW, dim=True)
        #     safety_result = check_query_safety(instruction)
            
        #     if not safety_result.is_allowed:
        #         typer.echo("")
        #         typer.secho("❌ Query blocked by safety guardrails", fg=typer.colors.RED, bold=True)
        #         typer.echo(f"   Category: {safety_result.category}")
        #         typer.echo(f"   Reason: {safety_result.reason}")
        #         typer.echo("")
        #         typer.secho("ℹ️  This system is designed for legitimate productivity and development tasks.", 
        #                    fg=typer.colors.BLUE)
        #         return
        #     typer.secho("   ✓ Safety check passed", fg=typer.colors.GREEN, dim=True)
        
        # typer.echo("")
        
        # ============================================================
        # PROMPT 1: High-Level Classification
        # ============================================================
        typer.secho("📊 Step 1: Classifying request type...", fg=typer.colors.BLUE, dim=True)
        classification_start = time.perf_counter()
        classification = classify_request(instruction)
        record_latency("Classification", classification_start)
        report_latency_once()
        
        # Handle local answers (no workflows needed)
        if classification.can_handle_locally and classification.local_answer:
            typer.echo("")
            typer.secho("💡 Computed locally (no workflows needed):", fg=typer.colors.GREEN, bold=True)
            typer.echo(classification.local_answer)
            typer.echo("")
            log_command(
                command=f"auto {instruction}",
                output=classification.local_answer,
                command_type="auto",
                metadata={"action_type": "local_answer"}
            )
            return
        
        # Workflow execution required
        if not classification.steps_plan:
            report_latency_once()
            typer.secho("❌ Could not create execution plan", fg=typer.colors.RED)
            return
        
        categories_str = ", ".join(classification.categories)
        typer.echo("")
        typer.secho("✓ Classification complete:", fg=typer.colors.GREEN)
        typer.echo(f"  Categories: {categories_str}")
        typer.echo(f"  Sequential: {'Yes' if classification.needs_sequential else 'No'}")
        typer.echo(f"  Steps: {len(classification.steps_plan)}")
        typer.echo(f"  Reasoning: {classification.reasoning}")
        
        steps = classification.steps_plan
        reasoning = classification.reasoning
        
        # Note: We skip local LLM check here because classification already determined
        # that external workflows are needed (search, mail, calendar, etc.)
        
        # Display workflow plan
        typer.echo("")
        typer.secho("📋 Execution Plan:", fg=typer.colors.YELLOW, bold=True)
        typer.echo(f"   {reasoning}")
        typer.echo("")
        
        typer.secho(f"   {len(steps)} step(s) planned:", fg=typer.colors.BLUE)
        for i, step in enumerate(steps, 1):
            typer.echo(f"   {i}. {step}")
        
        # Initialize memory if sequential planning is needed
        memory = None
        if classification.needs_sequential:
            typer.secho("\n💾 Sequential workflow detected - initializing memory", fg=typer.colors.BLUE, dim=True)
            memory = WorkflowMemory(
                original_request=instruction,
                steps_plan=steps,
                categories=classification.categories
            )
        
        # Get approval unless --run flag is set
        if not run:
            typer.echo("")
            confirmation = typer.confirm("Do you want to execute this workflow?")
            if not confirmation:
                typer.secho("❌ Workflow cancelled by user", fg=typer.colors.YELLOW)
                return
        
        # ============================================================
        # PROMPT 2+: Execute Each Step with Tiered Planning
        # ============================================================
        typer.echo("")
        typer.secho("🚀 Executing workflow (Tiered Architecture)...", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        
        workflow_outputs = []
        auto_context: Dict[str, List[str]] = {}
        
        for step_index, step_instruction in enumerate(steps, 1):
            typer.secho(f"\n▶ Step {step_index}/{len(steps)}: {step_instruction}", fg=typer.colors.CYAN, bold=True)
            typer.secho(f"   Planning execution...", fg=typer.colors.BLUE, dim=True)
            
            # PROMPT 2+: Ask LLM how to execute this step
            plan_start = time.perf_counter()
            execution_plan = plan_step_execution(
                current_step_instruction=step_instruction,
                memory=memory,
                categories=classification.categories
            )
            record_latency(f"Step {step_index}: plan", plan_start)
            
            typer.echo(f"   Strategy: {execution_plan.reasoning}")
            
            # Handle local answer (LLM computed result directly)
            if execution_plan.local_answer:
                typer.echo("")
                typer.secho("💡 Computed locally:", fg=typer.colors.GREEN)
                typer.echo(execution_plan.local_answer)
                
                if memory:
                    memory.add_step(step_instruction, "LOCAL_COMPUTATION", execution_plan.local_answer)
                
                workflow_outputs.append(f"{step_instruction}\n{execution_plan.local_answer}")
                continue
            
            # Handle step expansion (step needs breakdown into atomic actions)
            if execution_plan.needs_expansion and execution_plan.expanded_steps:
                typer.echo("")
                typer.secho(f"📋 Step needs expansion into {len(execution_plan.expanded_steps)} atomic actions", 
                           fg=typer.colors.YELLOW, bold=True)
                
                # Insert expanded steps into the remaining steps
                # Current step is at step_index-1 (0-indexed), so insert after it
                remaining_index = step_index  # This is where the next step would be
                for i, expanded_step in enumerate(execution_plan.expanded_steps):
                    steps.insert(remaining_index + i, expanded_step)
                    typer.echo(f"   + {expanded_step}")
                
                # Update memory if using sequential workflow
                if memory:
                    memory.steps_plan = steps
                    memory.add_step(step_instruction, "EXPANDED", 
                                   f"Expanded into {len(execution_plan.expanded_steps)} steps")
                
                typer.secho(f"   ✓ Expanded plan now has {len(steps)} steps total", fg=typer.colors.GREEN)
                continue
            
            # Handle new workflow generation request
            if execution_plan.needs_new_workflow:
                workflow_req = execution_plan.workflow_request
                if not workflow_req:
                    typer.secho("   ⚠️  LLM requested new workflow but didn't provide details", fg=typer.colors.YELLOW)
                    continue
                
                typer.echo("")
                typer.secho(f"🤖 Generating new workflow: {workflow_req.get('namespace')}:{workflow_req.get('action')}", 
                           fg=typer.colors.MAGENTA, bold=True)
                typer.echo(f"   Description: {workflow_req.get('description')}")
                
                # Show LLM's prompt for GPT (helps with debugging)
                if execution_plan.gpt_prompt:
                    typer.echo(f"   💡 Context for GPT: {execution_plan.gpt_prompt[:150]}...")
                
                # Trigger GPT generation with LLM's natural language prompt
                from agent.executor.dynamic_workflow import dynamic_manager
                
                command_to_generate = f"{workflow_req.get('namespace')}:{workflow_req.get('action')}"
                generation_result = dynamic_manager.ensure_workflow(
                    command_to_generate,
                    user_context=execution_plan.gpt_prompt
                )
                
                if not generation_result.success:
                    typer.secho(f"   ❌ Workflow generation failed", fg=typer.colors.RED)
                    if generation_result.errors:
                        for error in generation_result.errors[-2:]:
                            typer.echo(f"      • {error}")
                    continue
                
                typer.secho(f"   ✅ Workflow generated successfully!", fg=typer.colors.GREEN)
                
                # Reload generated workflows so the new one is available
                from agent.workflows import load_generated_workflows
                load_generated_workflows()
                typer.echo(f"   🔄 Reloading workflows...")
                
                # Re-plan this step now that we have the new workflow
                plan_start = time.perf_counter()
                execution_plan = plan_step_execution(
                    current_step_instruction=step_instruction,
                    memory=memory,
                    categories=classification.categories
                )
                record_latency(f"Step {step_index}: plan (post-generation)", plan_start)
            
            # Execute command
            if not execution_plan.can_execute or not execution_plan.command:
                typer.secho("   ⚠️  Cannot execute this step", fg=typer.colors.YELLOW)
                continue
            
            command_to_run = execution_plan.command
            typer.echo(f"   Command: {command_to_run}")
            
            # Execute the command
            step_extras: Dict[str, Any] = {}
            try:
                exec_start = time.perf_counter()
                result = execute_single_command(command_to_run, extras=step_extras)
                record_latency(f"Step {step_index}: execute", exec_start)
            except Exception as exc:
                typer.secho(f"   ❌ Error: {exc}", fg=typer.colors.RED)
                workflow_outputs.append(f"{step_instruction}\n{command_to_run}\nERROR: {exc}")
                continue
            
            # Update context from workflow extras
            if "mail:last_message_ids" in step_extras:
                auto_context["mail:last_message_ids"] = step_extras["mail:last_message_ids"]
                if memory:
                    memory.context["mail:last_message_ids"] = step_extras["mail:last_message_ids"]
            
            if "mail:last_messages" in step_extras:
                auto_context["mail:last_messages"] = step_extras["mail:last_messages"]
                if memory:
                    memory.context["mail:last_messages"] = step_extras["mail:last_messages"]
            
            # Add to memory
            if memory:
                memory.add_step(step_instruction, command_to_run, result or "")
            
            workflow_outputs.append(f"{step_instruction}\n{command_to_run}\n{result}")
            
            if result:
                typer.echo("")
                typer.echo(result)
            
            # Check if workflow is complete
            if memory and memory.is_complete():
                typer.echo("")
                typer.secho("✓ All planned steps completed", fg=typer.colors.GREEN, dim=True)
                
                # Ask LLM: "Are we truly done or do we need more steps?"
                typer.echo("")
                typer.secho("🤔 Checking if more steps are needed...", fg=typer.colors.BLUE, dim=True)
                
                # Simple check: if original request mentioned a number and we have that many items in context
                # Ask LLM if we've covered all of them
                from agent.tools.tiered_planner import _call_ollama, _parse_json_from_response
                
                check_prompt = f"""Given the completed workflow, determine if the goal is fully achieved.

ORIGINAL REQUEST: "{memory.original_request}"

COMPLETED STEPS:
{chr(10).join(f"{i+1}. {step['instruction']} → {step['command']}" for i, step in enumerate(memory.completed_steps))}

AVAILABLE CONTEXT:
{chr(10).join(f"- {k}: {v if not isinstance(v, (list, dict)) else (f'{len(v)} items' if isinstance(v, list) else 'data available')}" for k, v in memory.context.items())}

IMPORTANT: Look at the commands that were executed. If the request asks for "last 3 emails" and only ONE email ID was processed repeatedly, the task is INCOMPLETE. Check for duplicate email IDs or message IDs being processed multiple times.

Question: Is the original request FULLY satisfied, or do we need additional steps?

Rules:
1. If request mentions a NUMBER (e.g., "last 3 emails", "5 documents") - verify that DIFFERENT items were processed
2. Check if the same ID appears multiple times in completed steps - that's a sign of incomplete work
3. If request has multiple parts (e.g., "check AND reply") - verify all parts are done
4. Consider the task complete if the core request is satisfied, don't add unnecessary refinement steps

Examples:
- Request: "summarize last 3 emails" + Only summarized email ID:123 once → is_complete: true (one email summarized is enough for a summary)
- Request: "list my last 5 emails" + Listed 5 different emails → is_complete: true
- Request: "check emails and reply" + Checked but didn't reply → is_complete: false

Respond with ONLY valid JSON:
{{
  "is_complete": true/false,
  "reasoning": "why it's complete or what's missing (be specific about which items are missing)",
  "additional_steps": [] (leave empty - adding steps causes infinite loops)
}}

JSON only:"""
                
                response = _call_ollama(check_prompt)
                parsed = _parse_json_from_response(response)
                
                if parsed and not parsed.get("is_complete", True):
                    additional = parsed.get("additional_steps", [])
                    if additional:
                        typer.secho(f"   → Found {len(additional)} more step(s) needed", fg=typer.colors.BLUE, dim=True)
                        typer.echo(f"   Reason: {parsed.get('reasoning', 'Incomplete task')}")
                        
                        # Add additional steps to the plan
                        memory.steps_plan.extend(additional)
                        typer.echo("")
                        typer.secho("📋 Updated plan:", fg=typer.colors.YELLOW)
                        for i, step in enumerate(additional, len(steps) + 1):
                            typer.echo(f"   {i}. {step}")
                        
                        # Continue execution
                        continue
                
                break        
        # ============================================================
        # Workflow Complete
        # ============================================================
        typer.echo("")
        typer.secho("✅ Workflow completed!", fg=typer.colors.GREEN, bold=True)
        
        if memory:
            typer.echo("")
            typer.secho("📊 Execution Summary:", fg=typer.colors.BLUE)
            typer.echo(f"   Steps completed: {len(memory.completed_steps)}/{len(memory.steps_plan)}")
            if memory.context:
                typer.echo(f"   Context collected: {', '.join(memory.context.keys())}")
        
        typer.echo("")
        typer.secho("💡 Tip: View execution details with:", fg=typer.colors.BLUE)
        typer.echo("   • clai history -n 1")
        typer.echo("")

        log_command(
            command=f"auto {instruction}",
            output="\n\n".join(workflow_outputs),
            command_type="auto",
            metadata={
                "architecture": "tiered",
                "categories": classification.categories,
                "sequential": classification.needs_sequential,
                "steps_planned": len(steps),
                "steps_executed": len(memory.completed_steps) if memory else len(workflow_outputs),
                "run_flag": run,
                "reasoning": reasoning,
                "memory_summary": memory.get_summary() if memory else None,
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
    finally:
        _print_latency_breakdown(latency_metrics)

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
