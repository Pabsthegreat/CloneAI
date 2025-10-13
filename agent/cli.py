import re
import os
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
    

def execute_single_command(action: str) -> str:
    """Execute a single command and return result."""
    
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
            
            # Log the command
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"count": count, "sender": sender, "action": "list"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            
            # Log the error
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"count": count, "sender": sender, "action": "list", "error": True}
            )
            return error_msg
    
    # Parse mail:view command (view full email)
    elif action.startswith("mail:view"):
        from agent.tools.mail import get_full_email
        
        # Extract message ID
        id_match = re.search(r'id:([^\s]+)', action, re.IGNORECASE)
        
        if not id_match:
            error_msg = "❌ mail:view requires: id:MESSAGE_ID"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "view", "error": True}
            )
            return error_msg
        
        try:
            result = get_full_email(id_match.group(1))
            log_command(
                command=f"do {action}",
                output=f"Viewed email {id_match.group(1)}",
                command_type="mail",
                metadata={"message_id": id_match.group(1), "action": "view"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "view", "error": True}
            )
            return error_msg
    
    # Parse mail:download command (download attachments)
    elif action.startswith("mail:download"):
        from agent.tools.mail import download_email_attachments
        
        # Extract message ID
        id_match = re.search(r'id:([^\s]+)', action, re.IGNORECASE)
        dir_match = re.search(r'dir:([^\s]+)', action, re.IGNORECASE)
        
        if not id_match:
            error_msg = "❌ mail:download requires: id:MESSAGE_ID [dir:PATH]"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "download", "error": True}
            )
            return error_msg
        
        try:
            save_dir = dir_match.group(1) if dir_match else None
            result = download_email_attachments(id_match.group(1), save_dir)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"message_id": id_match.group(1), "action": "download"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "download", "error": True}
            )
            return error_msg
    
    # Parse mail:scan-meetings command
    elif action.startswith("mail:scan-meetings"):
        from agent.tools.mail import scan_emails_for_meetings
        
        # Extract hours parameter
        hours_match = re.search(r'hours:(\d+)', action, re.IGNORECASE)
        hours = int(hours_match.group(1)) if hours_match else 24
        
        try:
            result = scan_emails_for_meetings(hours)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"hours": hours, "action": "scan_meetings"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "scan_meetings", "error": True}
            )
            return error_msg
    
    # Parse mail:add-meeting command
    elif action.startswith("mail:add-meeting"):
        from agent.tools.mail import add_meeting_from_email
        
        # Extract email ID
        id_match = re.search(r'email-id:([^\s]+)', action, re.IGNORECASE)
        time_match = re.search(r'time:([^\s]+)', action, re.IGNORECASE)
        
        if not id_match:
            error_msg = "❌ mail:add-meeting requires: email-id:MESSAGE_ID [time:DATETIME]"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "add_meeting", "error": True}
            )
            return error_msg
        
        try:
            custom_time = time_match.group(1) if time_match else None
            result = add_meeting_from_email(id_match.group(1), custom_time)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"message_id": id_match.group(1), "action": "add_meeting"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "add_meeting", "error": True}
            )
            return error_msg
    
    # Parse mail:invite command (create and send meeting invite)
    elif action.startswith("mail:invite"):
        from agent.tools.mail import create_and_send_meeting_invite
        
        # Extract parameters
        to_match = re.search(r'to:([^\s]+)', action, re.IGNORECASE)
        subject_match = re.search(r'subject:([^:]+?)(?:\s+(?:time|duration|platform|message):|$)', action, re.IGNORECASE)
        time_match = re.search(r'time:([\d\-T:]+)(?=\s+|$)', action, re.IGNORECASE)
        duration_match = re.search(r'duration:(\d+)', action, re.IGNORECASE)
        platform_match = re.search(r'platform:([^\s]+)', action, re.IGNORECASE)
        message_match = re.search(r'message:(.+?)(?:\s+(?:to|subject|time|duration|platform):|$)', action, re.IGNORECASE)
        
        if not to_match or not subject_match or not time_match:
            error_msg = "❌ mail:invite requires: to:EMAIL subject:TEXT time:DATETIME [duration:MINS] [platform:gmeet/zoom/teams]"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "invite", "error": True}
            )
            return error_msg
        
        try:
            result = create_and_send_meeting_invite(
                to=to_match.group(1),
                subject=subject_match.group(1).strip(),
                time=time_match.group(1),
                duration=int(duration_match.group(1)) if duration_match else 60,
                platform=platform_match.group(1) if platform_match else 'gmeet',
                message=message_match.group(1).strip() if message_match else None
            )
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"to": to_match.group(1), "action": "invite"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "invite", "error": True}
            )
            return error_msg
    
    # Parse mail:priority command (list priority emails)
    elif action.startswith("mail:priority ") or action == "mail:priority":
        from agent.tools.priority_emails import get_priority_emails
        
        # Parse "last N" pattern
        count = 10  # default
        count_match = re.search(r'last\s+(\d+)', action, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        
        try:
            result = get_priority_emails(count)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"count": count, "action": "priority"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority", "error": True}
            )
            return error_msg
    
    # Parse mail:priority-add command
    elif action.startswith("mail:priority-add"):
        from agent.tools.priority_emails import add_priority_sender
        
        # Extract email/domain
        parts = action.split(maxsplit=1)
        if len(parts) < 2:
            error_msg = "❌ mail:priority-add requires: EMAIL or @DOMAIN"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority_add", "error": True}
            )
            return error_msg
        
        try:
            identifier = parts[1].strip()
            result = add_priority_sender(identifier)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"identifier": identifier, "action": "priority_add"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority_add", "error": True}
            )
            return error_msg
    
    # Parse mail:priority-remove command
    elif action.startswith("mail:priority-remove"):
        from agent.tools.priority_emails import remove_priority_sender
        
        # Extract email/domain
        parts = action.split(maxsplit=1)
        if len(parts) < 2:
            error_msg = "❌ mail:priority-remove requires: EMAIL or @DOMAIN"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority_remove", "error": True}
            )
            return error_msg
        
        try:
            identifier = parts[1].strip()
            result = remove_priority_sender(identifier)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"identifier": identifier, "action": "priority_remove"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority_remove", "error": True}
            )
            return error_msg
    
    # Parse mail:priority-list command
    elif action.startswith("mail:priority-list"):
        from agent.tools.priority_emails import list_priority_senders
        
        try:
            result = list_priority_senders()
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"action": "priority_list"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "priority_list", "error": True}
            )
            return error_msg
    
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
            error_msg = "❌ Draft requires: to:email subject:text body:text\nExample: clai do \"mail:draft to:user@test.com subject:Hello body:Hi there\""
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "draft", "error": True}
            )
            return error_msg
        
        try:
            result = create_draft_email(
                to=to_match.group(1),
                subject=subject_match.group(1).strip(),
                body=body_match.group(1).strip(),
                cc=cc_match.group(1) if cc_match else None,
                bcc=bcc_match.group(1) if bcc_match else None
            )
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="mail",
                metadata={"to": to_match.group(1), "action": "draft"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="mail",
                metadata={"action": "draft", "error": True}
            )
            return error_msg
    
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
            
            log_command(
                command=f"do {action}",
                output=result,
                command_type="calendar",
                metadata={"count": count, "action": "list"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="calendar",
                metadata={"action": "list", "error": True}
            )
            return error_msg
    
    # Parse tasks command (list scheduled tasks)
    elif action == "tasks":
        from agent.tools.scheduler import list_scheduled_tasks
        
        try:
            result = list_scheduled_tasks()
            log_command(
                command=f"do {action}",
                output=result,
                command_type="scheduler",
                metadata={"action": "list_tasks"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "list_tasks", "error": True}
            )
            return error_msg
    
    # Parse task:add command
    elif action.startswith("task:add"):
        from agent.tools.scheduler import add_scheduled_task
        
        # Extract parameters
        name_match = re.search(r'name:([^\s]+?)(?:\s+(?:command|time):|$)', action, re.IGNORECASE)
        command_match = re.search(r'command:([^\s]+?)(?:\s+(?:name|time):|$)', action, re.IGNORECASE)
        time_match = re.search(r'time:([\d:]+)(?=\s+|$)', action, re.IGNORECASE)
        
        if not name_match or not command_match or not time_match:
            error_msg = "❌ task:add requires: name:NAME command:COMMAND time:HH:MM\nExample: clai do \"task:add name:Check Email command:mail:list time:12:00\""
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "add_task", "error": True}
            )
            return error_msg
        
        try:
            result = add_scheduled_task(
                name=name_match.group(1).strip(),
                command=command_match.group(1).strip(),
                time=time_match.group(1).strip()
            )
            log_command(
                command=f"do {action}",
                output=result,
                command_type="scheduler",
                metadata={"name": name_match.group(1), "action": "add_task"}
            )
            return result
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "add_task", "error": True}
            )
            return error_msg
    
    # Parse task:remove command
    elif action.startswith("task:remove"):
        from agent.tools.scheduler import remove_scheduled_task
        
        # Extract task ID
        parts = action.split()
        if len(parts) < 2:
            error_msg = "❌ task:remove requires: TASK_ID\nExample: clai do \"task:remove 1\""
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "remove_task", "error": True}
            )
            return error_msg
        
        try:
            task_id = int(parts[1])
            result = remove_scheduled_task(task_id)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="scheduler",
                metadata={"task_id": task_id, "action": "remove_task"}
            )
            return result
        except ValueError:
            error_msg = "❌ Invalid task ID. Must be a number."
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "remove_task", "error": True}
            )
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "remove_task", "error": True}
            )
            return error_msg
    
    # Parse task:toggle command
    elif action.startswith("task:toggle"):
        from agent.tools.scheduler import toggle_scheduled_task
        
        # Extract task ID
        parts = action.split()
        if len(parts) < 2:
            error_msg = "❌ task:toggle requires: TASK_ID\nExample: clai do \"task:toggle 1\""
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "toggle_task", "error": True}
            )
            return error_msg
        
        try:
            task_id = int(parts[1])
            result = toggle_scheduled_task(task_id)
            log_command(
                command=f"do {action}",
                output=result,
                command_type="scheduler",
                metadata={"task_id": task_id, "action": "toggle_task"}
            )
            return result
        except ValueError:
            error_msg = "❌ Invalid task ID. Must be a number."
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "toggle_task", "error": True}
            )
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            log_command(
                command=f"do {action}",
                output=error_msg,
                command_type="scheduler",
                metadata={"action": "toggle_task", "error": True}
            )
            return error_msg
    
    else:
        error_msg = f"❌ Unknown action: {action}"
        help_text = """
Supported actions:
  📧 Email - Basic:
    - mail:list [last N] [email@domain.com]
    - mail:view id:MESSAGE_ID
    - mail:download id:MESSAGE_ID [dir:PATH]
    - mail:drafts [last N]
    - mail:draft to:EMAIL subject:TEXT body:TEXT
    - mail:send to:EMAIL subject:TEXT body:TEXT [attachments:PATH1,PATH2]
    
  📧 Email - Meetings:
    - mail:scan-meetings [hours:N]
    - mail:add-meeting email-id:MESSAGE_ID [time:DATETIME]
    - mail:invite to:EMAIL subject:TEXT time:DATETIME [duration:MINS]
    
  � Email - Priority:
    - mail:priority [last N]
    - mail:priority-add EMAIL or @DOMAIN
    - mail:priority-remove EMAIL or @DOMAIN
    - mail:priority-list
    
  📅 Calendar:
    - calendar:create title:TEXT start:DATETIME [duration:MINUTES]
    - calendar:list [next N]
    
  ⏰ Scheduler:
    - tasks
    - task:add name:NAME command:COMMAND time:HH:MM
    - task:remove TASK_ID
    - task:toggle TASK_ID
    
  🔗 Cascading:
    - Use && to chain commands: "mail:scan-meetings && mail:priority last 5"
"""
        
        # Log the error
        log_command(
            command=f"do {action}",
            output=error_msg,
            command_type="do",
            metadata={"action": action, "error": True}
        )
        return error_msg + help_text

@app.command()
def interpret(
    message: str = typer.Argument(..., help="Natural language instruction"),
    auto_run: bool = typer.Option(False, "--run", "-r", help="Automatically execute the parsed command"),
    model: str = typer.Option("qwen3:4b-instruct", "--model", "-m", help="Ollama model to use")
):
    """
    Parse natural language into CloneAI commands using Ollama.
    
    This command uses a local LLM (via Ollama) to translate your natural language
    instructions into proper CloneAI command syntax.
    
    Examples:
        clai interpret "show me my last 10 emails"
        clai interpret "list emails from john@example.com"
        clai interpret "create a meeting tomorrow at 2pm" --run
        clai interpret "download attachments from message abc123"
        clai interpret "show my calendar for next week" --model qwen3:4b-instruct
    
    Note: Requires Ollama to be installed (https://ollama.ai)
          And the model to be pulled: ollama pull qwen3:4b-instruct
    """
    typer.echo("")
    typer.secho(f"🧠 Interpreting: {message}", fg=typer.colors.CYAN)
    typer.echo("")
    
    try:
        from agent.tools.nl_parser import parse_natural_language
        
        # Parse the natural language
        typer.echo("⏳ Calling Ollama LLM...")
        result = parse_natural_language(message, model=model)
        
        if not result["success"]:
            typer.secho(f"❌ Failed to parse command: {result['explanation']}", fg=typer.colors.RED)
            log_command(
                command=f"interpret: {message}",
                output=f"Failed: {result['explanation']}",
                command_type="interpret",
                metadata={"input": message, "success": False}
            )
            return
        
        # Display result
        typer.echo("")
        typer.secho("✅ Parsed command:", fg=typer.colors.GREEN)
        typer.secho(f"   {result['command']}", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.echo("")
        typer.secho(f"💡 Explanation: {result['explanation']}", fg=typer.colors.YELLOW)
        typer.secho(f"📊 Confidence: {result['confidence']}", fg=typer.colors.BLUE)
        typer.echo("")
        
        # Log the interpretation
        log_command(
            command=f"interpret: {message}",
            output=f"Parsed: {result['command']}",
            command_type="interpret",
            metadata={
                "input": message,
                "parsed_command": result['command'],
                "confidence": result['confidence'],
                "auto_run": auto_run
            }
        )
        
        # Auto-run if requested
        if auto_run:
            typer.secho("🚀 Executing command...", fg=typer.colors.MAGENTA)
            typer.echo("")
            
            # Execute the parsed command using the do() function
            try:
                do(result['command'])
            except Exception as e:
                typer.secho(f"❌ Error executing command: {str(e)}", fg=typer.colors.RED)
        else:
            typer.echo("💡 To execute this command, run:")
            typer.secho(f'   clai do "{result["command"]}"', fg=typer.colors.BRIGHT_WHITE, bold=True)
            typer.echo("")
            typer.echo("   Or use --run flag to execute automatically:")
            typer.secho(f'   clai interpret "{message}" --run', fg=typer.colors.BRIGHT_WHITE, bold=True)
        
    except ImportError as e:
        typer.secho(f"❌ Error: {str(e)}", fg=typer.colors.RED)
        typer.echo("Make sure nl_parser.py is in agent/tools/")
    except Exception as e:
        typer.secho(f"❌ Unexpected error: {str(e)}", fg=typer.colors.RED)
        import traceback
        traceback.print_exc()

@app.command()
def draft_email(
    instruction: str = typer.Argument(..., help="Natural language instruction for the email"),
    recipient: Optional[str] = typer.Option(None, "--to", "-t", help="Override recipient email"),
    send: bool = typer.Option(False, "--send", "-s", help="Send immediately without confirmation"),
    model: str = typer.Option("qwen3:4b-instruct", "--model", "-m", help="Ollama model to use")
):
    """
    Draft an email using AI and send it after approval.
    
    This command uses a local LLM (via Ollama) to generate professional email content
    from your natural language instruction. It shows you a preview and asks for
    confirmation before sending.
    
    Examples:
        clai draft-email "send an email to john@example.com about the project deadline"
        clai draft-email "email sarah about tomorrow's meeting being rescheduled to 3pm"
        clai draft-email "write to support@company.com asking about billing issue" --to support@company.com
        clai draft-email "thank bob@test.com for the feedback" --send
    
    Note: Requires Ollama to be installed (https://ollama.ai)
          And the model to be pulled: ollama pull qwen3:4b-instruct
    """
    typer.echo("")
    typer.secho(f"✍️  Drafting email: {instruction}", fg=typer.colors.CYAN)
    typer.echo("")
    
    try:
        from agent.tools.nl_parser import generate_email_content
        
        # Generate email content
        typer.echo("⏳ Generating email content with AI...")
        result = generate_email_content(instruction, model=model)
        
        if not result["success"]:
            typer.secho(f"❌ Failed to generate email: {result.get('error', 'Unknown error')}", fg=typer.colors.RED)
            return
        
        # Override recipient if provided
        if recipient:
            result["to"] = recipient
        
        # Display the generated email
        typer.echo("")
        typer.secho("=" * 80, fg=typer.colors.BRIGHT_BLACK)
        typer.secho("📧 DRAFT EMAIL", fg=typer.colors.GREEN, bold=True)
        typer.secho("=" * 80, fg=typer.colors.BRIGHT_BLACK)
        typer.echo("")
        typer.secho(f"To: {result['to']}", fg=typer.colors.BLUE, bold=True)
        typer.secho(f"Subject: {result['subject']}", fg=typer.colors.BLUE, bold=True)
        typer.echo("")
        typer.secho("-" * 80, fg=typer.colors.BRIGHT_BLACK)
        typer.echo(result['body'])
        typer.secho("-" * 80, fg=typer.colors.BRIGHT_BLACK)
        typer.echo("")
        
        # Check if recipient email is valid
        if result['to'] == "RECIPIENT_EMAIL" or "@" not in result['to']:
            typer.secho("⚠️  Warning: No valid recipient email detected!", fg=typer.colors.YELLOW)
            typer.echo("Please specify recipient with --to flag")
            typer.echo("")
            override_to = typer.prompt("Enter recipient email address")
            result['to'] = override_to
            typer.echo("")
        
        # Log the draft
        log_command(
            command=f"draft-email: {instruction}",
            output=f"Generated email to {result['to']} with subject: {result['subject']}",
            command_type="draft-email",
            metadata={
                "instruction": instruction,
                "to": result['to'],
                "subject": result['subject'],
                "body_preview": result['body'][:100]
            }
        )
        
        # Ask for confirmation unless --send flag is used
        if not send:
            typer.echo("")
            typer.secho("Options:", fg=typer.colors.CYAN, bold=True)
            typer.echo("  [s] Send now")
            typer.echo("  [d] Save as draft")
            typer.echo("  [e] Edit and send")
            typer.echo("  [c] Cancel")
            typer.echo("")
            
            choice = typer.prompt("What would you like to do?", default="s").lower()
            
            if choice == "c":
                typer.secho("❌ Cancelled", fg=typer.colors.RED)
                return
            elif choice == "e":
                typer.echo("")
                typer.secho("✏️  Edit mode:", fg=typer.colors.YELLOW)
                result['subject'] = typer.prompt("Subject", default=result['subject'])
                typer.echo("Body (press Enter twice when done):")
                body_lines = []
                while True:
                    line = input()
                    if line == "" and (not body_lines or body_lines[-1] == ""):
                        break
                    body_lines.append(line)
                result['body'] = "\n".join(body_lines[:-1] if body_lines and body_lines[-1] == "" else body_lines)
                typer.echo("")
        
        # Determine action: send or draft
        action = "send" if (send or (not send and choice == "s")) else "draft"
        
        if action == "send":
            # Send the email
            typer.secho("📤 Sending email...", fg=typer.colors.MAGENTA)
            from agent.tools.mail import send_email_now
            
            send_result = send_email_now(
                to=result['to'],
                subject=result['subject'],
                body=result['body']
            )
            typer.echo("")
            typer.echo(send_result)
            
        else:
            # Save as draft
            typer.secho("💾 Saving as draft...", fg=typer.colors.MAGENTA)
            from agent.tools.mail import create_draft_email
            
            draft_result = create_draft_email(
                to=result['to'],
                subject=result['subject'],
                body=result['body']
            )
            typer.echo("")
            typer.echo(draft_result)
        
    except ImportError as e:
        typer.secho(f"❌ Error: {str(e)}", fg=typer.colors.RED)
        typer.echo("Make sure all required modules are available")
    except KeyboardInterrupt:
        typer.echo("")
        typer.secho("❌ Cancelled by user", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"❌ Unexpected error: {str(e)}", fg=typer.colors.RED)
        import traceback
        traceback.print_exc()

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
        
        typer.secho(f"\n🔄 Parsing workflow: '{instruction}'", fg=typer.colors.CYAN, bold=True)
        
        # Parse the workflow
        result = parse_workflow(instruction)
        
        if not result["success"]:
            typer.secho(f"❌ Failed to parse workflow: {result.get('error', 'Unknown error')}", fg=typer.colors.RED)
            return
        
        steps = result["steps"]
        reasoning = result.get("reasoning", "")
        
        # Display workflow plan
        typer.echo("")
        typer.secho("📋 Workflow Plan:", fg=typer.colors.YELLOW, bold=True)
        typer.echo(f"   {reasoning}")
        typer.echo("")
        
        typer.secho(f"   {len(steps)} step(s) identified:", fg=typer.colors.BLUE)
        for i, step in enumerate(steps, 1):
            command = step["command"]
            description = step["description"]
            needs_approval = "⚠️  Needs approval" if step["needs_approval"] else "✓ Auto-execute"
            
            typer.echo(f"\n   Step {i}: {description}")
            typer.echo(f"           Command: {command}")
            typer.echo(f"           {needs_approval}")
        
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
        
        # Check if this is a "check emails and reply" workflow
        is_reply_workflow = any("reply" in step["description"].lower() or "draft" in step["description"].lower() 
                                for step in steps)
        
        if is_reply_workflow:
            # Handle the full email reply workflow
            typer.secho("🤖 Automated Email Reply Workflow", fg=typer.colors.MAGENTA, bold=True)
            typer.echo("")
            
            # Step 1: Fetch emails
            typer.secho("📧 Step 1: Fetching emails...", fg=typer.colors.CYAN)
            
            # Parse first step to get count and sender filter
            first_step = steps[0]
            parts = first_step["command"].split()
            count = 3  # default
            sender = None
            
            # Look for sender email in command (after "from")
            for i, part in enumerate(parts):
                if part.isdigit():
                    count = int(part)
                elif part.lower() == "from" and i + 1 < len(parts):
                    sender = parts[i + 1]
            
            from agent.tools.mail import GmailClient
            client = GmailClient()
            # Fetch emails - if sender specified, filter by "from:sender" (emails received FROM that address)
            messages = client.list_messages(max_results=count, sender=sender)
            
            if not messages:
                typer.secho(f"   No emails found", fg=typer.colors.YELLOW)
                return
            
            typer.secho(f"   ✓ Found {len(messages)} email(s)", fg=typer.colors.GREEN)
            typer.echo("")
            
            # Step 2: Generate drafts for each email
            typer.secho("✍️  Step 2: Generating professional replies...", fg=typer.colors.CYAN)
            drafts = []
            
            from agent.tools.mail import get_full_email
            from agent.tools.nl_parser import generate_email_content
            
            for idx, msg in enumerate(messages, 1):
                msg_id = msg['id']
                subject = msg['subject']
                sender_email = msg['from']
                
                # Extract just email address from "Name <email>" format
                import re
                email_match = re.search(r'<(.+?)>', sender_email)
                reply_to = email_match.group(1) if email_match else sender_email
                
                typer.echo(f"   [{idx}/{len(messages)}] Processing: {subject[:50]}...")
                
                # Fetch full email content
                full_email = get_full_email(msg_id)
                
                # Generate reply using LLM
                prompt = f"Generate a professional reply to this email:\n\nOriginal Email:\n{full_email}\n\nWrite a polite and professional response."
                
                result = generate_email_content(prompt)
                
                if result["success"]:
                    reply_subject = result["subject"]
                    reply_body = result["body"]
                    
                    # Create draft
                    draft_result = client.create_draft(
                        to=reply_to,
                        subject=f"Re: {subject}",
                        body=reply_body
                    )
                    
                    draft_id = draft_result['id']
                    drafts.append({
                        'id': draft_id,
                        'number': idx,
                        'to': reply_to,
                        'subject': f"Re: {subject}",
                        'body': reply_body,
                        'original_subject': subject
                    })
                    
                    typer.secho(f"      ✓ Draft created", fg=typer.colors.GREEN)
                else:
                    typer.secho(f"      ⚠️  Failed to generate reply: {result.get('error', 'Unknown error')}", fg=typer.colors.YELLOW)
            
            if not drafts:
                typer.secho("\n❌ No drafts were created", fg=typer.colors.RED)
                return
            
            # Step 3: Show all drafts and get approval
            typer.echo("")
            typer.secho("=" * 80, fg=typer.colors.BLUE)
            typer.secho("📝 GENERATED DRAFTS - REVIEW & APPROVE", fg=typer.colors.YELLOW, bold=True)
            typer.secho("=" * 80, fg=typer.colors.BLUE)
            typer.echo("")
            
            for draft in drafts:
                typer.secho(f"[Draft #{draft['number']}]", fg=typer.colors.CYAN, bold=True)
                typer.echo(f"To: {draft['to']}")
                typer.echo(f"Subject: {draft['subject']}")
                typer.echo(f"Original: {draft['original_subject'][:60]}...")
                typer.echo("")
                typer.echo("Body:")
                typer.echo(draft['body'])
                typer.echo("")
                typer.secho("-" * 80, fg=typer.colors.BLUE)
                typer.echo("")
            
            # Get approval
            typer.secho("📮 Ready to send drafts!", fg=typer.colors.GREEN, bold=True)
            typer.echo("")
            typer.echo("Options:")
            typer.echo("  • Type 'all' to send all drafts")
            typer.echo("  • Type specific numbers (e.g., '1,3' or '1 3' or '2')")
            typer.echo("  • Press Enter to cancel")
            typer.echo("")
            
            approval = typer.prompt("Which drafts to send?", default="", show_default=False)
            
            if not approval or approval.strip() == "":
                typer.secho("\n❌ Cancelled - No drafts sent", fg=typer.colors.YELLOW)
                typer.echo(f"💡 Drafts are saved in Gmail. Use 'clai do mail:list-drafts' to view them.")
                return
            
            # Parse approval
            to_send = []
            approval = approval.strip().lower()
            
            if approval == "all":
                to_send = list(range(1, len(drafts) + 1))
            else:
                # Parse comma or space separated numbers
                numbers_str = approval.replace(',', ' ')
                try:
                    to_send = [int(n) for n in numbers_str.split() if n.isdigit()]
                except ValueError:
                    typer.secho("\n❌ Invalid input. Cancelled.", fg=typer.colors.RED)
                    return
            
            # Send approved drafts
            typer.echo("")
            typer.secho("📤 Sending approved drafts...", fg=typer.colors.GREEN, bold=True)
            typer.echo("")
            
            from agent.tools.mail import send_draft_email
            
            sent_count = 0
            for num in to_send:
                if 1 <= num <= len(drafts):
                    draft = drafts[num - 1]
                    typer.echo(f"   [{num}/{len(to_send)}] Sending to {draft['to']}...")
                    
                    result = send_draft_email(draft['id'])
                    if "successfully" in result.lower():
                        typer.secho(f"      ✓ Sent!", fg=typer.colors.GREEN)
                        sent_count += 1
                    else:
                        typer.secho(f"      ⚠️  Failed: {result}", fg=typer.colors.YELLOW)
                else:
                    typer.secho(f"   ⚠️  Invalid draft number: {num}", fg=typer.colors.YELLOW)
            
            typer.echo("")
            typer.secho(f"✅ Workflow Complete! Sent {sent_count}/{len(to_send)} emails", fg=typer.colors.GREEN, bold=True)
            return
        
        # Standard workflow execution for non-reply workflows
        context = {}  # Store context between steps
        
        for i, step in enumerate(steps, 1):
            command = step["command"]
            description = step["description"]
            needs_approval = step["needs_approval"]
            
            typer.secho(f"▶ Step {i}/{len(steps)}: {description}", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"   Executing: {command}")
            typer.echo("")
            
            # Parse command into parts
            parts = command.split()
            if len(parts) < 2:
                typer.secho(f"   ⚠️  Invalid command format: {command}", fg=typer.colors.YELLOW)
                continue
            
            action = parts[0]
            subcommand = parts[1] if len(parts) > 1 else None
            args = parts[2:] if len(parts) > 2 else []
            
            # Handle different command types
            if action == "mail:list":
                # Extract count from "last N" or just N
                count = 10  # default
                sender = None
                
                # Parse arguments
                if "last" in args:
                    last_idx = args.index("last")
                    if last_idx + 1 < len(args):
                        try:
                            count = int(args[last_idx + 1])
                        except ValueError:
                            pass
                elif args and args[0].isdigit():
                    count = int(args[0])
                
                # Check for "from" sender filter
                if "from" in args:
                    from_idx = args.index("from")
                    if from_idx + 1 < len(args):
                        sender = args[from_idx + 1]
                
                from agent.tools.mail import list_emails
                result = list_emails(count=count, sender=sender)
                typer.echo(result)
                context["last_list_result"] = result  # Store for potential replies
            
            elif action == "mail:invite":
                typer.secho("   ⚠️  Meeting invites require interactive input", fg=typer.colors.YELLOW)
                typer.echo("   Use 'clai do mail:invite' for full functionality")
            
            elif action == "calendar:create":
                typer.secho("   ⚠️  Calendar events require interactive input", fg=typer.colors.YELLOW)
                typer.echo("   Use 'clai do calendar:create' for full functionality")
            
            else:
                typer.secho(f"   ⚠️  Command type '{action}' not yet supported in auto mode", fg=typer.colors.YELLOW)
                typer.echo(f"   Run manually: clai interpret \"{command}\"")
            
            # Ask for approval for sensitive operations
            if needs_approval and not run:
                typer.echo("")
                continue_workflow = typer.confirm(f"Continue to step {i + 1}?", default=True)
                if not continue_workflow:
                    typer.secho(f"\n⚠️  Workflow stopped at step {i}", fg=typer.colors.YELLOW)
                    return
            
            typer.echo("")
        
        typer.secho("✅ Workflow completed!", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        typer.secho("💡 Tip: For full interactive control, use individual commands:", fg=typer.colors.BLUE)
        typer.echo("   • clai interpret \"your instruction\"")
        typer.echo("   • clai draft-email \"your message\"")
        typer.echo("   • clai do mail:reply <message-id>")
        
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
