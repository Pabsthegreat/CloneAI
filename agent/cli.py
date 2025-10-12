import re
import typer
from typing import Optional
from agent.state import log_command, get_history, search_history, format_history_list, get_logger
from agent.system_info import print_system_info

app = typer.Typer(help="Your personal CLI agent", no_args_is_help=True)

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
    Execute actions with the AI agent.
    
    Examples:
        # Email - List & View
        clai do "mail:list last 5"                    - List last 5 emails
        clai do "mail:list xyz@gmail.com"             - List emails from sender
        clai do "mail:drafts"                         - List all drafts
        clai do "mail:drafts last 5"                  - List last 5 drafts
        
        # Email - Create & Send
        clai do "mail:draft to:xyz@test.com subject:Hello body:Hi there"
        clai do "mail:send to:xyz@test.com subject:Hello body:Hi there"
        clai do "mail:send to:xyz@test.com subject:Doc body:See attached attachments:C:\\file.pdf"
        clai do "mail:send draft-id:r123456789"       - Send existing draft
        
        # Calendar
        clai do "calendar:create title:Team Standup start:2025-10-15T10:00:00 duration:30"
        clai do "calendar:list next 5"                - List next 5 events
    """
    typer.echo("")
    typer.secho(f"🤖 Executing: {action}", fg=typer.colors.YELLOW)
    typer.echo("")
    
    # Parse mail:list commands
    if action.startswith("mail:list"):
        from agent.tools.mail import list_emails
        
        # Extract parameters
        count = 5  # default
        sender = None
        
        # Parse "last N" pattern
        last_match = re.search(r'last\s+(\d+)', action, re.IGNORECASE)
        if last_match:
            count = int(last_match.group(1))
        
        # Parse email address pattern
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', action)
        if email_match:
            sender = email_match.group(1)
        
        # Execute
        try:
            result = list_emails(count=count, sender=sender)
            typer.echo(result)
            
            # Log the command
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"count": count, "sender": sender, "action": "list"}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            
            # Log the error
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"count": count, "sender": sender, "action": "list", "error": True}
            )
    
    # Parse mail:draft commands
    elif action.startswith("mail:draft"):
        from agent.tools.mail import create_draft_email
        
        # Extract parameters using regex
        to_match = re.search(r'to:([^\s]+)', action, re.IGNORECASE)
        subject_match = re.search(r'subject:([^:]+?)(?:\s+(?:body|cc|bcc):|$)', action, re.IGNORECASE)
        body_match = re.search(r'body:(.+?)(?:\s+(?:cc|bcc):|$)', action, re.IGNORECASE)
        cc_match = re.search(r'cc:([^\s]+)', action, re.IGNORECASE)
        bcc_match = re.search(r'bcc:([^\s]+)', action, re.IGNORECASE)
        
        if not to_match or not subject_match or not body_match:
            error_msg = "❌ Draft requires: to:email subject:text body:text"
            typer.secho(error_msg, fg=typer.colors.RED)
            typer.echo("Example: clai do \"mail:draft to:user@test.com subject:Hello body:Hi there\"")
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "draft", "error": True}
            )
            return
        
        try:
            result = create_draft_email(
                to=to_match.group(1),
                subject=subject_match.group(1).strip(),
                body=body_match.group(1).strip(),
                cc=cc_match.group(1) if cc_match else None,
                bcc=bcc_match.group(1) if bcc_match else None
            )
            typer.echo(result)
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"to": to_match.group(1), "action": "draft"}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "draft", "error": True}
            )
    
    # Parse mail:drafts command (list all drafts)
    elif action.startswith("mail:drafts"):
        from agent.tools.mail import list_drafts_emails
        
        # Parse "last N" pattern
        count = 10  # default
        count_match = re.search(r'(?:last|next)\s+(\d+)', action, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        
        try:
            result = list_drafts_emails(count=count)
            typer.echo(result)
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"count": count, "action": "list_drafts"}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "list_drafts", "error": True}
            )
    
    # Parse mail:send command (send email directly)
    elif action.startswith("mail:send ") and "draft-id:" not in action:
        from agent.tools.mail import send_email_now
        
        # Extract parameters using regex
        to_match = re.search(r'to:([^\s]+)', action, re.IGNORECASE)
        subject_match = re.search(r'subject:([^:]+?)(?:\s+(?:body|cc|bcc|attachments):|$)', action, re.IGNORECASE)
        body_match = re.search(r'body:(.+?)(?:\s+(?:cc|bcc|attachments):|$)', action, re.IGNORECASE)
        cc_match = re.search(r'cc:([^\s]+)', action, re.IGNORECASE)
        bcc_match = re.search(r'bcc:([^\s]+)', action, re.IGNORECASE)
        attachments_match = re.search(r'attachments:(.+?)(?:\s+(?:cc|bcc):|$)', action, re.IGNORECASE)
        
        if not to_match or not subject_match or not body_match:
            error_msg = "❌ Send requires: to:email subject:text body:text"
            typer.secho(error_msg, fg=typer.colors.RED)
            typer.echo("Example: clai do \"mail:send to:user@test.com subject:Hello body:Hi there\"")
            typer.echo("With attachments: clai do \"mail:send to:user@test.com subject:Doc body:See attached attachments:C:\\file.pdf,C:\\image.jpg\"")
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "send", "error": True}
            )
            return
        
        # Parse attachments (comma-separated paths)
        attachments = None
        if attachments_match:
            attachments = [path.strip() for path in attachments_match.group(1).split(',')]
        
        try:
            result = send_email_now(
                to=to_match.group(1),
                subject=subject_match.group(1).strip(),
                body=body_match.group(1).strip(),
                cc=cc_match.group(1) if cc_match else None,
                bcc=bcc_match.group(1) if bcc_match else None,
                attachments=attachments
            )
            typer.echo(result)
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"to": to_match.group(1), "action": "send", "attachments": len(attachments) if attachments else 0}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "send", "error": True}
            )
    
    # Parse mail:send draft-id command (send existing draft)
    elif action.startswith("mail:send") and "draft-id:" in action:
        from agent.tools.mail import send_draft_email
        
        # Extract draft ID
        draft_id_match = re.search(r'draft-id:([^\s]+)', action, re.IGNORECASE)
        
        if not draft_id_match:
            error_msg = "❌ Send draft requires: draft-id:DRAFT_ID"
            typer.secho(error_msg, fg=typer.colors.RED)
            typer.echo("Example: clai do \"mail:send draft-id:r123456789\"")
            typer.echo("Get draft IDs with: clai do \"mail:drafts\"")
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "send_draft", "error": True}
            )
            return
        
        try:
            result = send_draft_email(draft_id=draft_id_match.group(1))
            typer.echo(result)
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"draft_id": draft_id_match.group(1), "action": "send_draft"}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "send_draft", "error": True}
            )
    
    # Parse calendar:create commands
    elif action.startswith("calendar:create"):
        from agent.tools.calendar import create_calendar_event
        
        # Try structured format first: title:X start:Y duration:Z
        title_match = re.search(r'title:([^:]+?)(?=\s+(?:start|end|location|description|duration):|$)', action, re.IGNORECASE)
        start_match = re.search(r'start:([\d\-T:]+)(?=\s+|$)', action, re.IGNORECASE)
        end_match = re.search(r'end:([\d\-T:]+)(?=\s+|$)', action, re.IGNORECASE)
        duration_match = re.search(r'duration:(\d+)', action, re.IGNORECASE)
        location_match = re.search(r'location:([^\s]+?)(?=\s+(?:start|end|title|description|duration):|$)', action, re.IGNORECASE)
        description_match = re.search(r'description:(.+?)(?=\s+(?:start|end|title|location|duration):|$)', action, re.IGNORECASE)
        
        # If structured format found
        if title_match and start_match:
            try:
                result = create_calendar_event(
                    summary=title_match.group(1).strip(),
                    start_time=start_match.group(1).strip(),
                    end_time=end_match.group(1).strip() if end_match else None,
                    duration_minutes=int(duration_match.group(1)) if duration_match else 60,
                    location=location_match.group(1).strip() if location_match else None,
                    description=description_match.group(1).strip() if description_match else None
                )
                typer.echo(result)
                
                log_command(
                    command=f"do {action}",
                    output=result,
                    command_type="calendar",
                    metadata={"action": "create", "title": title_match.group(1).strip()}
                )
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                typer.secho(error_msg, fg=typer.colors.RED)
                log_command(
                    command=f"do {action}",
                    output=error_msg,
                    command_type="calendar",
                    metadata={"action": "create", "error": True}
                )
        else:
            # Natural language format - extract what we can
            error_msg = "❌ Calendar event requires: title:X start:Y [duration:Z]"
            typer.secho(error_msg, fg=typer.colors.RED)
            typer.echo("Example: clai do \"calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60\"")
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="calendar",
                metadata={"action": "create", "error": True}
            )
    
    # Parse calendar:list commands
    elif action.startswith("calendar:list"):
        from agent.tools.calendar import list_calendar_events
        
        # Parse "next N" or "last N" pattern
        count = 10  # default
        count_match = re.search(r'(?:next|last)\s+(\d+)', action, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        
        try:
            result = list_calendar_events(count=count)
            typer.echo(result)
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="calendar",
                metadata={"count": count, "action": "list"}
            )
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            typer.secho(error_msg, fg=typer.colors.RED)
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="calendar",
                metadata={"action": "list", "error": True}
            )
    
    else:
        error_msg = f"❌ Unknown action: {action}"
        typer.secho(error_msg, fg=typer.colors.RED)
        typer.echo("\nSupported actions:")
        typer.echo("  📧 Email:")
        typer.echo("    - mail:list [last N] [email@domain.com]")
        typer.echo("    - mail:drafts [last N]")
        typer.echo("    - mail:draft to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [bcc:EMAIL]")
        typer.echo("    - mail:send to:EMAIL subject:TEXT body:TEXT [cc:EMAIL] [attachments:PATH1,PATH2]")
        typer.echo("    - mail:send draft-id:DRAFT_ID")
        typer.echo("  📅 Calendar:")
        typer.echo("    - calendar:create title:TEXT start:DATETIME [duration:MINUTES]")
        typer.echo("    - calendar:list [next N]")
        
        # Log the error
        log_command(
            command=f"do {action}",
            output=error_msg,
            command_type="do",
            metadata={"action": action, "error": True}
        )

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

if __name__ == "__main__":
    app()
