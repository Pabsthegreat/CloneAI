"""
CloneAI Desktop API Server

FastAPI server that provides REST endpoints for the Electron desktop app.
Wraps existing CloneAI CLI functionality into web APIs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import importlib
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

# CloneAI imports
from agent.cli import execute_single_command
from agent.core.planning.tiered import classify_request, plan_step_execution, WorkflowMemory
from agent.workflows import registry as workflow_registry
from agent.system_artifacts import ArtifactsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="CloneAI Desktop API",
    description="REST API for CloneAI Desktop Application",
    version="1.0.0"
)

# CORS middleware for Electron renderer process
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to app://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Startup: Load API Keys from Config
# ============================================================================

@app.on_event("startup")
async def load_api_keys_on_startup():
    """
    Load API keys from config file and set as environment variables.
    This ensures that the API keys stored in the UI are actually used by the code.
    """
    try:
        # Initialize artifacts directories
        ArtifactsManager.initialize()
        logger.info(f"Initialized artifacts directory at: {ArtifactsManager.get_artifacts_dir()}")
        
        # Load API keys
        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Set each key as an environment variable
            for key, value in config.items():
                os.environ[key] = value
                logger.info(f"Loaded API key: {key}")
            
            logger.info(f"Loaded {len(config)} API keys from {config_path}")
        else:
            logger.info(f"No config file found at {config_path}, using existing environment variables")
    except Exception as e:
        logger.error(f"Failed to load API keys on startup: {e}", exc_info=True)


# ============================================================================
# Request/Response Models
# ============================================================================

class CommandRequest(BaseModel):
    """Execute a direct CloneAI command"""
    command: str = Field(..., description="Command string (e.g., 'mail:list last 5')")
    extras: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")


class ChatRequest(BaseModel):
    """Natural language chat request"""
    message: str = Field(..., description="Natural language message")
    execute: bool = Field(default=False, description="Execute workflow immediately or just classify")


class WorkflowExecuteRequest(BaseModel):
    """Execute a specific workflow"""
    workflow_id: str = Field(..., description="Workflow ID from classification")
    approve: bool = Field(default=True, description="User approval to execute")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Workflow parameters")


class GenerateWorkflowRequest(BaseModel):
    """Generate new workflow via GPT"""
    namespace: str = Field(..., description="Workflow namespace (e.g., 'system', 'search')")
    name: str = Field(..., description="Workflow name (e.g., 'product_prices')")
    user_request: str = Field(..., description="Natural language description of workflow")


class WorkflowResponse(BaseModel):
    """Workflow metadata"""
    namespace: str
    name: str
    summary: str
    parameters: List[Dict[str, Any]]
    usage: Optional[str] = None


class FileOperationRequest(BaseModel):
    """Request for file operations (merge, convert, etc)"""
    operation: str = Field(..., description="Operation: merge_pdf, convert_doc, etc")
    file_ids: List[str] = Field(..., description="List of uploaded file IDs")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Operation-specific parameters")


class ConfigUpdateRequest(BaseModel):
    """Update configuration/secrets"""
    key: str = Field(..., description="Config key (e.g., OPENAI_API_KEY)")
    value: str = Field(..., description="Config value")
    category: Optional[str] = Field(default="api", description="Config category: api, credentials, settings")


class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict[str, Any]]


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/info")
async def get_system_info():
    """Get system and CloneAI configuration info"""
    try:
        from agent.system_info import get_config_dir
        config_dir = get_config_dir()
        
        workflows = list(workflow_registry.list())
        
        return {
            "success": True,
            "config_dir": str(config_dir),
            "workflows_count": len(workflows),
            "custom_workflows_dir": str(config_dir / "workflows" / "custom"),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/features")
async def get_available_features():
    """
    Return platform-specific feature availability.
    Used by frontend to show/hide features based on system capabilities.
    """
    import platform
    import shutil
    
    def has_libreoffice() -> bool:
        return shutil.which('libreoffice') is not None
    
    def has_ms_office() -> bool:
        if platform.system() != 'Windows':
            return False
        try:
            import comtypes.client
            word = comtypes.client.CreateObject('Word.Application')
            word.Quit()
            return True
        except:
            return False
    
    return {
        "email": True,
        "calendar": True,
        "web_search": True,
        "pdf_merge": True,
        "pdf_to_docx": True,
        "docx_to_pdf": has_libreoffice() or has_ms_office(),
        "ppt_to_pdf": has_libreoffice() or has_ms_office(),
        "image_generation": True,
        "voice_mode": False,  # TODO: Implement voice mode
        "office_installed": has_ms_office(),
        "libreoffice_installed": has_libreoffice(),
        "platform": platform.system()
    }


# ============================================================================
# Command Execution Endpoints
# ============================================================================

@app.post("/api/execute")
async def execute_command(req: CommandRequest):
    """
    Execute a direct CloneAI command.
    
    Example: {"command": "mail:list last 5"}
    """
    try:
        logger.info(f"Executing command: {req.command}")
        # Run blocking command in thread pool to avoid blocking event loop
        result = await run_in_threadpool(execute_single_command, req.command, extras=req.extras)
        
        return {
            "success": True,
            "command": req.command,
            "output": result
        }
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/analyze")
async def analyze_chat_request(req: ChatRequest):
    """
    Analyze natural language request without executing.
    Returns classification and execution plan.
    """
    try:
        logger.info(f"Analyzing request: {req.message}")
        
        # Use tiered planner to classify request (run in thread pool)
        classification = await run_in_threadpool(classify_request, req.message)
        
        response = {
            "success": True,
            "message": req.message,
            "can_handle_locally": classification.can_handle_locally,
            "local_answer": classification.local_answer,
            "categories": classification.categories,
            "needs_sequential": classification.needs_sequential,
            "steps_plan": classification.steps_plan,
            "reasoning": classification.reasoning
        }
        
        # If it needs sequential execution, provide preview
        if classification.needs_sequential and classification.steps_plan:
            response["requires_approval"] = True
            response["preview_steps"] = "\n".join([f"{i+1}. {step}" for i, step in enumerate(classification.steps_plan)])
        
        return response
        
    except Exception as e:
        logger.error(f"Chat analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Natural language chat interface.
    Classifies request and optionally executes it.
    """
    try:
        logger.info(f"Chat request: {req.message} (execute={req.execute})")
        
        # Classify request (run in thread pool)
        classification = await run_in_threadpool(classify_request, req.message)
        
        response = {
            "success": True,
            "message": req.message,
            "can_handle_locally": classification.can_handle_locally,
            "local_answer": classification.local_answer,
            "categories": classification.categories,
            "needs_sequential": classification.needs_sequential,
            "steps_plan": classification.steps_plan,
            "reasoning": classification.reasoning
        }
        
        # Execute if requested
        if req.execute:
            # If it can be handled locally, return the answer
            if classification.can_handle_locally and classification.local_answer:
                response["executed"] = True
                response["output"] = classification.local_answer
            
            # Multi-step workflow execution using tiered planner (matching CLI behavior)
            elif classification.needs_sequential and classification.steps_plan:
                response["executed"] = True
                response["multi_step"] = True
                response["steps_executed"] = []
                
                logger.info(f"Executing multi-step workflow with {len(classification.steps_plan)} steps")
                logger.info(f"Original message: {req.message}")
                
                # Use tiered planner for step-by-step execution (same as CLI)
                try:
                    # Initialize memory with required arguments
                    memory = WorkflowMemory(
                        original_request=req.message,
                        steps_plan=classification.steps_plan,
                        categories=classification.categories
                    )
                    
                    all_outputs = []
                    
                    for step_index, step_instruction in enumerate(classification.steps_plan, 1):
                        logger.info(f"▶ Step {step_index}/{len(classification.steps_plan)}: {step_instruction}")
                        
                        try:
                            # Use plan_step_execution to convert natural language to CLI command
                            # This matches the CLI's behavior exactly
                            execution_plan = await run_in_threadpool(
                                plan_step_execution,
                                current_step_instruction=step_instruction,
                                memory=memory,
                                categories=classification.categories
                            )
                            
                            logger.info(f"   Strategy: {execution_plan.reasoning}")
                            
                            # Handle local answer (LLM computed result directly)
                            if execution_plan.local_answer:
                                logger.info(f"   💡 Computed locally")
                                
                                memory.add_step(step_instruction, "LOCAL_COMPUTATION", execution_plan.local_answer)
                                all_outputs.append(execution_plan.local_answer)
                                
                                response["steps_executed"].append({
                                    "step": step_index,
                                    "description": step_instruction,
                                    "command": "LOCAL_COMPUTATION",
                                    "status": "success",
                                    "output": execution_plan.local_answer[:500]
                                })
                                continue
                            
                            # Handle step expansion
                            if execution_plan.needs_expansion and execution_plan.expanded_steps:
                                logger.info(f"   📋 Step needs expansion into {len(execution_plan.expanded_steps)} steps")
                                # For now, just note it - full expansion support could be added later
                                memory.add_step(step_instruction, "EXPANDED", 
                                              f"Expanded into {len(execution_plan.expanded_steps)} steps")
                                response["steps_executed"].append({
                                    "step": step_index,
                                    "description": step_instruction,
                                    "status": "expanded",
                                    "expanded_steps": execution_plan.expanded_steps
                                })
                                continue
                            
                            # Execute command
                            if not execution_plan.can_execute or not execution_plan.command:
                                logger.warning(f"   ⚠ Cannot execute this step")
                                response["steps_executed"].append({
                                    "step": step_index,
                                    "description": step_instruction,
                                    "status": "skipped",
                                    "reason": "Cannot execute - no command available"
                                })
                                continue
                            
                            command_to_run = execution_plan.command
                            logger.info(f"   Command: {command_to_run}")
                            
                            # Validate command format before executing
                            if not command_to_run or ':' not in command_to_run:
                                error_msg = f"Invalid command format: '{command_to_run}'. Expected 'namespace:action param:value'"
                                logger.error(f"   ✗ {error_msg}")
                                response["steps_executed"].append({
                                    "step": step_index,
                                    "description": step_instruction,
                                    "command": command_to_run,
                                    "status": "failed",
                                    "error": error_msg
                                })
                                continue
                            
                            # Execute the CLI command (in thread pool)
                            step_output = await run_in_threadpool(execute_single_command, command_to_run)
                            
                            # Store in memory for next step
                            memory.add_step(
                                step_instruction=step_instruction,
                                command=command_to_run,
                                output=str(step_output)
                            )
                            
                            all_outputs.append(step_output)
                            
                            logger.info(f"   ✓ Step {step_index} completed successfully")
                            
                            response["steps_executed"].append({
                                "step": step_index,
                                "description": step_instruction,
                                "command": command_to_run,
                                "status": "success",
                                "output": str(step_output)[:500]  # Show more output
                            })
                        
                        except Exception as step_error:
                            error_msg = str(step_error)
                            if "Commands must include a namespace" in error_msg:
                                error_msg = f"{error_msg} Command attempted: '{command_to_run if 'command_to_run' in locals() else 'unknown'}'"
                            logger.error(f"   ✗ Step {step_index} failed: {error_msg}", exc_info=True)
                            response["steps_executed"].append({
                                "step": step_index,
                                "description": step_instruction,
                                "command": command_to_run if 'command_to_run' in locals() else 'N/A',
                                "status": "failed",
                                "error": error_msg
                            })
                            # Continue to next step instead of breaking (resilient execution)
                    
                    # Combine all outputs
                    if all_outputs:
                        response["output"] = "\n\n---\n\n".join(str(o) for o in all_outputs)
                    else:
                        response["output"] = "Multi-step execution completed (no output generated)"
                    
                    logger.info(f"✓ Multi-step execution completed: {len(all_outputs)}/{len(classification.steps_plan)} steps successful")
                    
                except Exception as exec_error:
                    logger.error(f"Multi-step execution failed: {exec_error}", exc_info=True)
                    response["executed"] = False
                    response["error"] = str(exec_error)
            
            # Single-step workflow execution
            else:
                try:
                    # ALWAYS use tiered planner to convert natural language to CLI command
                    logger.info(f"Planning single-step execution: {req.message}")
                    
                    # Use the first step from steps_plan
                    step_instruction = classification.steps_plan[0] if classification.steps_plan else req.message
                    
                    # Initialize memory
                    memory = WorkflowMemory(
                        original_request=req.message,
                        steps_plan=classification.steps_plan,
                        categories=classification.categories
                    )
                    
                    # Plan the step execution
                    execution_plan = plan_step_execution(
                        current_step_instruction=step_instruction,
                        memory=memory,
                        categories=classification.categories
                    )
                    
                    # Handle local answer
                    if execution_plan.local_answer:
                        response["executed"] = True
                        response["output"] = execution_plan.local_answer
                    # Execute the command
                    elif execution_plan.can_execute and execution_plan.command:
                            # Check if this is a mail:send command - if so, create draft instead
                            if execution_plan.command.startswith("mail:send"):
                                logger.info(f"Creating email draft for: {execution_plan.command}")
                                
                                # Parse the command to extract email parameters
                                import shlex
                                parts = shlex.split(execution_plan.command)
                                email_params = {}
                                for part in parts[1:]:  # Skip 'mail:send'
                                    if ':' in part:
                                        key, value = part.split(':', 1)
                                        email_params[key] = value
                                
                                # Create draft
                                draft_id = str(uuid.uuid4())
                                email_drafts[draft_id] = {
                                    "draft_id": draft_id,
                                    "to": email_params.get("to", ""),
                                    "subject": email_params.get("subject", ""),
                                    "body": email_params.get("body", ""),
                                    "cc": email_params.get("cc"),
                                    "bcc": email_params.get("bcc"),
                                    "attachments": email_params.get("attachments", "").split(",") if email_params.get("attachments") else [],
                                    "created_at": datetime.now().isoformat(),
                                    "status": "pending",
                                    "command": execution_plan.command
                                }
                                
                                response["executed"] = False
                                response["draft_id"] = draft_id
                                response["requires_confirmation"] = True
                                response["draft"] = email_drafts[draft_id]
                                response["output"] = "Email draft created. Please review and confirm."
                            else:
                                logger.info(f"Executing command: {execution_plan.command}")
                                result = execute_single_command(execution_plan.command)
                                response["executed"] = True
                                response["output"] = result
                                
                                # Check if result contains an image path
                                if isinstance(result, str) and "artifacts/" in result:
                                    # Extract filename from path
                                    import re
                                    match = re.search(r'artifacts/([^\s]+\.(png|jpg|jpeg|gif))', result)
                                    if match:
                                        image_filename = match.group(1)
                                        response["image_url"] = f"/api/artifacts/{image_filename}"
                                        response["image_filename"] = image_filename
                    # Needs new workflow
                    elif execution_plan.needs_new_workflow:
                        response["executed"] = False
                        response["output"] = f"This requires a new workflow to be generated. {execution_plan.reasoning}"
                    else:
                        response["executed"] = False
                        response["output"] = f"Could not execute: {execution_plan.reasoning}"
                    
                except Exception as exec_error:
                    logger.error(f"Execution failed: {exec_error}", exc_info=True)
                    response["executed"] = False
                    response["error"] = str(exec_error)
        else:
            # Preview mode
            if classification.needs_sequential and classification.steps_plan:
                response["preview_steps"] = "\n".join([f"{i+1}. {step}" for i, step in enumerate(classification.steps_plan)])
            elif classification.local_answer:
                response["preview_steps"] = f"Local answer: {classification.local_answer}"
        
        return response
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Management Endpoints
# ============================================================================
# (Moved to line 1557 to avoid duplication)


# ============================================================================
# Email Draft & Send Confirmation
# ============================================================================

# In-memory draft storage
email_drafts: Dict[str, Dict[str, Any]] = {}


class EmailDraftRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    attachments: Optional[List[str]] = None


@app.post("/api/email/draft")
async def create_email_draft(draft: EmailDraftRequest):
    """Create an email draft for confirmation before sending"""
    try:
        draft_id = str(uuid.uuid4())
        email_drafts[draft_id] = {
            "draft_id": draft_id,
            "to": draft.to,
            "subject": draft.subject,
            "body": draft.body,
            "cc": draft.cc,
            "bcc": draft.bcc,
            "attachments": draft.attachments or [],
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        logger.info(f"Created email draft: {draft_id}")
        
        return {
            "success": True,
            "draft_id": draft_id,
            "draft": email_drafts[draft_id]
        }
        
    except Exception as e:
        logger.error(f"Failed to create email draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/send/{draft_id}")
async def send_email_draft(draft_id: str):
    """Send a confirmed email draft"""
    try:
        if draft_id not in email_drafts:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        draft = email_drafts[draft_id]
        
        # Build mail:send command
        command = f'mail:send to:"{draft["to"]}" subject:"{draft["subject"]}" body:"{draft["body"]}"'
        
        if draft.get("cc"):
            command += f' cc:"{draft["cc"]}"'
        if draft.get("bcc"):
            command += f' bcc:"{draft["bcc"]}"'
        if draft.get("attachments"):
            command += f' attachments:{",".join(draft["attachments"])}'
        
        logger.info(f"Sending email draft {draft_id}: {command}")
        result = execute_single_command(command)
        
        # Update draft status
        draft["status"] = "sent"
        draft["sent_at"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "draft_id": draft_id,
            "result": result,
            "message": "Email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to send email draft: {e}")
        if draft_id in email_drafts:
            email_drafts[draft_id]["status"] = "failed"
            email_drafts[draft_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/email/draft/{draft_id}")
async def cancel_email_draft(draft_id: str):
    """Cancel/delete an email draft"""
    try:
        if draft_id not in email_drafts:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        del email_drafts[draft_id]
        logger.info(f"Cancelled email draft: {draft_id}")
        
        return {
            "success": True,
            "message": "Draft cancelled"
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel email draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/generate")
async def generate_workflow(req: GenerateWorkflowRequest):
    """
    Generate new workflow via GPT.
    
    This will be implemented when GPT workflow generation is ready.
    For now, returns placeholder.
    """
    try:
        logger.info(f"Generating workflow: {req.namespace}:{req.name}")
        
        # TODO: Implement GPT workflow generation
        # from agent.executor.gpt_workflow import generate_and_save_workflow
        # success = generate_and_save_workflow(
        #     namespace=req.namespace,
        #     name=req.name,
        #     user_request=req.user_request
        # )
        
        return {
            "success": False,
            "message": "Workflow generation not yet implemented",
            "namespace": req.namespace,
            "name": req.name
        }
        
    except Exception as e:
        logger.error(f"Workflow generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Email & Calendar Endpoints
# ============================================================================

@app.get("/api/emails")
async def get_emails(count: int = 20, unread_only: bool = False):
    """Get recent emails with proper formatting"""
    try:
        # Build command - no import needed, use execute_single_command
        if unread_only:
            command = f"mail:list last {count} unread"
        else:
            command = f"mail:list last {count}"
        
        logger.info(f"Fetching emails with command: {command}")
        result = execute_single_command(command)
        
        logger.info(f"Email result type: {type(result)}")
        logger.info(f"Email result preview: {str(result)[:500]}")
        
        # Parse the result - it's in numbered format
        emails = []
        if isinstance(result, str):
            # Split by the separator lines or numbered entries
            import re
            
            # Split by numbered entries (1., 2., etc.)
            email_blocks = re.split(r'\n\d+\.\s+Message ID:', result)
            
            for block in email_blocks[1:]:  # Skip first empty part
                lines = block.strip().split('\n')
                email = {}
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('From:'):
                        email['from'] = line[5:].strip()
                    elif line.startswith('Subject:'):
                        email['subject'] = line[8:].strip()
                    elif line.startswith('Date:'):
                        email['date'] = line[5:].strip()
                    elif line.startswith('Preview:'):
                        email['body'] = line[8:].strip()
                    elif line.startswith('Body:'):
                        email['body'] = line[5:].strip()
                
                if email:
                    # Ensure all required fields exist
                    email.setdefault('from', 'Unknown')
                    email.setdefault('subject', 'No Subject')
                    email.setdefault('date', '')
                    email.setdefault('body', 'No content')
                    emails.append(email)
        elif isinstance(result, list):
            emails = result
        
        return {
            "emails": emails,
            "count": len(emails),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar")
async def list_calendar_events(count: int = 10):
    """List upcoming calendar events in Google Calendar style format"""
    try:
        logger.info(f"Fetching {count} calendar events")
        
        # Execute command with proper syntax (no positional arg)
        cmd = f"calendar:list count:{count}"
        result = execute_single_command(cmd)
        
        # Parse and structure events for calendar view
        events = []
        if isinstance(result, str):
            lines = result.split('\n')
            current_event = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_event:
                        events.append(current_event)
                        current_event = {}
                elif line.startswith('Event:') or line.startswith('Title:'):
                    current_event['title'] = line.split(':', 1)[1].strip()
                elif line.startswith('Start:'):
                    current_event['start'] = line.split(':', 1)[1].strip()
                elif line.startswith('End:'):
                    current_event['end'] = line.split(':', 1)[1].strip()
                elif line.startswith('Location:'):
                    current_event['location'] = line.split(':', 1)[1].strip()
                elif line.startswith('Description:'):
                    current_event['description'] = line.split(':', 1)[1].strip()
            
            if current_event:
                events.append(current_event)
        elif isinstance(result, list):
            events = result
        
        return {
            "success": True,
            "count": len(events),
            "events": events,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# File Upload & Operations
# ============================================================================

# In-memory storage for uploaded files (use Redis/DB in production)
uploaded_files: Dict[str, Dict[str, Any]] = {}
temp_dir = Path(tempfile.gettempdir()) / "cloneai_uploads"
temp_dir.mkdir(exist_ok=True)


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for processing.
    Returns a file_id to reference in operations.
    """
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Save file to temp directory
        file_path = temp_dir / f"{file_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Store file metadata
        uploaded_files[file_id] = {
            "file_id": file_id,
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content),
            "content_type": file.content_type,
            "uploaded_at": datetime.now().isoformat()
        }
        
        logger.info(f"File uploaded: {file.filename} -> {file_id}")
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/operate")
async def perform_file_operation(req: FileOperationRequest):
    """
    Perform operations on uploaded files:
    - merge_pdf: Merge multiple PDFs
    - convert_doc: Convert document formats (doc->pdf, etc)
    - compress: Compress images/files
    - extract: Extract text from PDFs
    """
    try:
        operation = req.operation
        file_ids = req.file_ids
        params = req.params
        
        # Validate files exist
        for file_id in file_ids:
            if file_id not in uploaded_files:
                raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        result_file_id = str(uuid.uuid4())
        result_filename = f"result_{result_file_id}"
        
        # Execute operation based on type
        if operation == "merge_pdf":
            # Use doc:merge-pdf command from CloneAI
            file_paths = [uploaded_files[fid]["path"] for fid in file_ids]
            result_path = temp_dir / f"{result_filename}.pdf"
            
            # Quote file paths to handle spaces in filenames
            quoted_paths = ','.join([f'"{path}"' for path in file_paths])
            
            # Call merge workflow
            cmd = f'doc:merge-pdf files:{quoted_paths} output:"{result_path}"'
            logger.info(f"Executing: {cmd}")
            result = execute_single_command(cmd)
            logger.info(f"Merge result: {result}")
            
            # Verify the file was created
            if not result_path.exists():
                # Try artifacts folder (CloneAI default)
                artifacts_result = Path.cwd() / "artifacts" / f"{result_filename}.pdf"
                if artifacts_result.exists():
                    result_path = artifacts_result
                else:
                    raise HTTPException(status_code=500, detail=f"Merge failed: output file not created. Result: {result}")
            
            uploaded_files[result_file_id] = {
                "file_id": result_file_id,
                "filename": f"{result_filename}.pdf",
                "path": str(result_path),
                "size": result_path.stat().st_size,
                "content_type": "application/pdf",
                "created_at": datetime.now().isoformat()
            }
            
        elif operation == "convert_doc":
            # Convert document format
            source_file = uploaded_files[file_ids[0]]
            target_format = params.get("format", "pdf")
            result_path = temp_dir / f"{result_filename}.{target_format}"
            
            # Use appropriate conversion workflow based on format
            source_path = source_file['path']
            if source_path.endswith('.docx') and target_format == 'pdf':
                cmd = f'doc:docx-to-pdf input:"{source_path}" output:"{result_path}"'
            elif source_path.endswith('.pdf') and target_format == 'docx':
                cmd = f'doc:pdf-to-docx input:"{source_path}" output:"{result_path}"'
            elif source_path.endswith('.pptx') and target_format == 'pdf':
                cmd = f'doc:ppt-to-pdf input:"{source_path}" output:"{result_path}"'
            else:
                raise HTTPException(status_code=400, detail=f"Conversion from {source_path.split('.')[-1]} to {target_format} not supported")
            
            logger.info(f"Executing: {cmd}")
            result = execute_single_command(cmd)
            logger.info(f"Conversion result: {result}")
            
            # Verify the file was created
            if not result_path.exists():
                artifacts_result = Path.cwd() / "artifacts" / f"{result_filename}.{target_format}"
                if artifacts_result.exists():
                    result_path = artifacts_result
                else:
                    raise HTTPException(status_code=500, detail=f"Conversion failed: output file not created. Result: {result}")
            
            uploaded_files[result_file_id] = {
                "file_id": result_file_id,
                "filename": f"{result_filename}.{target_format}",
                "path": str(result_path),
                "size": result_path.stat().st_size,
                "content_type": f"application/{target_format}",
                "created_at": datetime.now().isoformat()
            }
            
        elif operation == "extract_text":
            # Extract text from PDF/document
            source_file = uploaded_files[file_ids[0]]
            
            # For now, return a placeholder since text extraction requires additional libraries
            # TODO: Add text extraction workflow
            return {
                "success": False,
                "operation": operation,
                "error": "Text extraction not yet implemented. Please install PyPDF2 or pdfplumber."
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {operation}")
        
        return {
            "success": True,
            "operation": operation,
            "result_file_id": result_file_id,
            "result_filename": uploaded_files[result_file_id]["filename"]
        }
        
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/download/{file_id}")
async def download_file(file_id: str):
    """Download a processed file"""
    try:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = uploaded_files[file_id]
        file_path = Path(file_info["path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found on disk: {file_path}")
        
        return FileResponse(
            path=str(file_path),
            filename=file_info["filename"],
            media_type=file_info.get("content_type", "application/octet-stream")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/artifacts/{filename}")
async def serve_artifact(filename: str):
    """Serve files from the artifacts folder (e.g., generated images)"""
    try:
        artifacts_dir = Path.cwd() / "artifacts"
        file_path = artifacts_dir / filename
        
        # Security: prevent path traversal
        if not file_path.resolve().is_relative_to(artifacts_dir.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {filename}")
        
        # Determine media type
        media_type = "application/octet-stream"
        if filename.endswith('.png'):
            media_type = "image/png"
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            media_type = "image/jpeg"
        elif filename.endswith('.gif'):
            media_type = "image/gif"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
        
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file"""
    try:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = uploaded_files[file_id]
        file_path = Path(file_info["path"])
        
        # Delete from disk
        if file_path.exists():
            file_path.unlink()
        
        # Remove from memory
        del uploaded_files[file_id]
        
        logger.info(f"Deleted file: {file_id}")
        
        return {"success": True, "message": "File deleted"}
        
    except Exception as e:
        logger.error(f"File deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Configuration & Secrets Management
# ============================================================================

def get_config_path() -> Path:
    """
    Get path to API keys config file (separate from OAuth credentials).
    
    Returns path to api_keys.json which stores OPENAI_API_KEY, SERPER_API_KEY, etc.
    This is separate from credentials.json which stores Google OAuth client secrets.
    """
    # Priority order for API keys config:
    # 1. Environment variable CLONEAI_API_KEYS_PATH
    # 2. User home directory ~/.clai/api_keys.json
    # 3. Project root api_keys.json
    
    env_path = os.environ.get('CLONEAI_API_KEYS_PATH')
    if env_path and Path(env_path).exists():
        return Path(env_path)
    
    possible_paths = [
        Path.home() / ".clai" / "api_keys.json",  # Separate file for API keys
        Path.cwd() / "api_keys.json",
        Path(__file__).parent.parent.parent / "api_keys.json"
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # Create default if none exist
    default_path = Path.home() / ".clai" / "api_keys.json"
    default_path.parent.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
    return default_path


@app.get("/api/config")
async def get_config():
    """
    Get current configuration (secrets masked).
    Returns available keys with masked values.
    """
    try:
        config_path = get_config_path()
        
        if not config_path.exists():
            return {
                "success": True,
                "config": {},
                "config_path": str(config_path),
                "keys": [],  # FIXED: Always include keys array
                "message": "No config file found"
            }
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Mask sensitive values
        masked_config = {}
        for key, value in config.items():
            if isinstance(value, str) and len(value) > 8:
                masked_config[key] = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked_config[key] = "*" * 8
        
        return {
            "success": True,
            "config": masked_config,
            "config_path": str(config_path),
            "keys": list(config.keys())
        }
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    """
    Update a configuration value.
    Creates config file if it doesn't exist and sets it as environment variable.
    """
    try:
        config_path = get_config_path()
        
        # Load existing config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Update value
        config[req.key] = req.value
        
        # Save config
        config_path.parent.mkdir(exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # IMPORTANT: Set as environment variable so it's immediately available
        os.environ[req.key] = req.value
        
        logger.info(f"Updated config key: {req.key} and set as environment variable")
        
        return {
            "success": True,
            "message": f"Updated {req.key}",
            "config_path": str(config_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/download")
async def download_config():
    """Download current config file (creates empty one if doesn't exist)"""
    try:
        config_path = get_config_path()
        
        # If file doesn't exist, create an empty one
        if not config_path.exists():
            config_path.parent.mkdir(exist_ok=True, mode=0o700)
            with open(config_path, 'w') as f:
                json.dump({}, f, indent=2)
            logger.info(f"Created empty config file at {config_path}")
        
        return FileResponse(
            path=str(config_path),
            filename="cloneai_api_keys.json",
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Failed to download config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/config/{key}")
async def delete_config_key(key: str):
    """Delete a configuration key and remove from environment variables"""
    try:
        config_path = get_config_path()
        
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Config file not found")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if key not in config:
            raise HTTPException(status_code=404, detail=f"Key not found: {key}")
        
        del config[key]
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # IMPORTANT: Remove from environment variables too
        if key in os.environ:
            del os.environ[key]
        
        logger.info(f"Deleted config key: {key} and removed from environment")
        
        return {
            "success": True,
            "message": f"Deleted {key}"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete config key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/google-oauth")
async def save_google_oauth_credentials(request: Request):
    """
    Save Google OAuth credentials to ~/.clai/credentials.json
    This is separate from the API keys file and used specifically for Gmail/Calendar OAuth.
    """
    try:
        body = await request.json()
        credentials_json = body.get('credentials')
        
        if not credentials_json:
            raise HTTPException(status_code=400, detail="Missing credentials")
        
        # Parse the credentials JSON
        credentials_data = json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json
        
        # Save to the OAuth credentials file (not api_keys.json)
        oauth_cred_path = Path.home() / ".clai" / "credentials.json"
        oauth_cred_path.parent.mkdir(exist_ok=True, mode=0o700)
        
        with open(oauth_cred_path, 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        os.chmod(oauth_cred_path, 0o600)  # Secure permissions
        
        logger.info(f"Saved Google OAuth credentials to: {oauth_cred_path}")
        
        return {
            "success": True,
            "message": "Google OAuth credentials saved",
            "path": str(oauth_cred_path)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Google credentials: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Failed to save Google OAuth credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/upload")
async def upload_credentials(file: UploadFile = File(...)):
    """Upload credentials JSON file"""
    try:
        config_path = get_config_path()
        
        # Read uploaded file
        content = await file.read()
        config_data = json.loads(content)
        
        # Validate it's a dict
        if not isinstance(config_data, dict):
            raise HTTPException(status_code=400, detail="Invalid credentials format")
        
        # Save to config path
        config_path.parent.mkdir(exist_ok=True, mode=0o700)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        os.chmod(config_path, 0o600)  # Secure permissions
        
        logger.info(f"Uploaded credentials to: {config_path}")
        
        return {
            "success": True,
            "message": f"Credentials uploaded successfully",
            "config_path": str(config_path),
            "keys_count": len(config_data)
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Failed to upload credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/keys/{key_name}")
async def get_api_key(key_name: str):
    """Get specific API key (for frontend display)"""
    try:
        config_path = get_config_path()
        
        if not config_path.exists():
            return {
                "success": False,
                "message": f"{key_name} not configured"
            }
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Map common key names
        key_mapping = {
            "openai": "OPENAI_API_KEY",
            "serper": "SERPER_API_KEY",
            "google": "GOOGLE_APPLICATION_CREDENTIALS"
        }
        
        actual_key = key_mapping.get(key_name.lower(), key_name)
        
        if actual_key in config:
            value = config[actual_key]
            # Mask the value
            if isinstance(value, str) and len(value) > 8:
                masked = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked = "*" * 8
            
            return {
                "success": True,
                "key": actual_key,
                "value": masked,
                "configured": True
            }
        
        return {
            "success": False,
            "key": actual_key,
            "configured": False
        }
        
    except Exception as e:
        logger.error(f"Failed to get API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Artifacts Management Endpoints
# ============================================================================

@app.get("/api/artifacts")
async def get_artifacts(artifact_type: Optional[str] = None):
    """
    Get list of all generated artifacts.
    
    Query params:
        artifact_type: Filter by type (images, documents, audio, all)
    """
    try:
        if artifact_type and artifact_type != "all":
            artifacts = ArtifactsManager.list_artifacts(artifact_type)
        else:
            artifacts = ArtifactsManager.list_artifacts()
        
        # Convert to serializable format
        artifacts_list = []
        for artifact_path in artifacts:
            stat = artifact_path.stat()
            artifacts_list.append({
                "name": artifact_path.name,
                "path": str(artifact_path),
                "type": artifact_path.parent.name,  # images, documents, etc.
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": artifact_path.suffix[1:] if artifact_path.suffix else "unknown"
            })
        
        # Sort by modification time (newest first)
        artifacts_list.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "success": True,
            "artifacts": artifacts_list,
            "count": len(artifacts_list),
            "base_path": str(ArtifactsManager.get_artifacts_dir())
        }
        
    except Exception as e:
        logger.error(f"Failed to get artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/artifacts/{artifact_type}/{filename}")
async def download_artifact(artifact_type: str, filename: str):
    """Download a specific artifact file."""
    try:
        file_path = ArtifactsManager.get_artifact_path(filename, artifact_type)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        media_type = "application/octet-stream"
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            media_type = f"image/{filename.split('.')[-1]}"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith('.pptx'):
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif filename.endswith(('.mp3', '.wav')):
            media_type = f"audio/{filename.split('.')[-1]}"
        
        # For images, don't force download - allow inline display
        headers = {}
        if not filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf')):
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Failed to download artifact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/artifacts/{artifact_type}/{filename}")
async def delete_artifact(artifact_type: str, filename: str):
    """Delete a specific artifact file."""
    try:
        file_path = ArtifactsManager.get_artifact_path(filename, artifact_type)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path.unlink()
        logger.info(f"Deleted artifact: {artifact_type}/{filename}")
        
        return {
            "success": True,
            "message": f"Deleted {filename}"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete artifact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chat Sessions Management
# ============================================================================

# In-memory chat sessions (use Redis/DB in production)
chat_sessions: Dict[str, ChatSession] = {}


@app.get("/api/chats")
async def list_chat_sessions():
    """List all chat sessions"""
    try:
        sessions = [
            {
                "session_id": s.session_id,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "message_count": len(s.messages)
            }
            for s in chat_sessions.values()
        ]
        
        # Sort by updated_at descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chats/new")
async def create_chat_session(title: Optional[str] = "New Chat"):
    """Create a new chat session"""
    try:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        session = ChatSession(
            session_id=session_id,
            title=title or "New Chat",
            created_at=now,
            updated_at=now,
            messages=[]
        )
        
        chat_sessions[session_id] = session
        
        logger.info(f"Created chat session: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "title": session.title,
            "created_at": session.created_at
        }
        
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{session_id}")
async def get_chat_session(session_id: str):
    """Get a specific chat session with all messages"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        return {
            "success": True,
            "session": session.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chats/{session_id}/message")
async def add_message_to_session(session_id: str, message: Dict[str, Any]):
    """Add a message to a chat session"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        # Add message
        message["timestamp"] = datetime.now().isoformat()
        session.messages.append(message)
        session.updated_at = datetime.now().isoformat()
        
        # Update title if it's the first user message
        if len(session.messages) == 1 and message.get("role") == "user":
            # Use first few words as title
            text = message.get("content", "New Chat")[:50]
            session.title = text if len(text) < 50 else text + "..."
        
        logger.info(f"Added message to session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message_count": len(session.messages)
        }
        
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chats/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        del chat_sessions[session_id]
        
        logger.info(f"Deleted chat session: {session_id}")
        
        return {
            "success": True,
            "message": "Chat session deleted"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/chats/{session_id}")
async def update_chat_session(session_id: str, title: Optional[str] = None):
    """Update chat session metadata"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        
        if title:
            session.title = title
        
        session.updated_at = datetime.now().isoformat()
        
        logger.info(f"Updated chat session: {session_id}")
        
        return {
            "success": True,
            "session": session.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to update chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflows Listing
# ============================================================================

@app.get("/api/workflows")
async def list_workflows():
    """List all available workflows with metadata"""
    try:
        workflows_data = []
        
        # workflow_registry is the WorkflowRegistry instance, not a module
        for workflow_info in workflow_registry.export_command_info():
            workflows_data.append({
                "command": f"{workflow_info['namespace']}:{workflow_info['name']}",
                "namespace": workflow_info['namespace'],
                "name": workflow_info['name'],
                "summary": workflow_info['summary'],
                "description": workflow_info['description'],
                "usage": workflow_info['usage'],
                "category": workflow_info['category'],
                "examples": workflow_info.get('examples', []),
                "preferred_llm": workflow_info.get('preferred_llm', 'local')
            })
        
        # Group by namespace
        by_namespace = {}
        for wf in workflows_data:
            ns = wf['namespace']
            if ns not in by_namespace:
                by_namespace[ns] = []
            by_namespace[ns].append(wf)
        
        return {
            "success": True,
            "workflows": workflows_data,
            "by_namespace": by_namespace,
            "total": len(workflows_data)
        }
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Settings Management
# ============================================================================

# In-memory settings (use Redis/DB in production)
app_settings: Dict[str, Any] = {
    "keyboard_shortcut": "CommandOrControl+Shift+A",
    "theme": "system",
    "auto_start": False,
    "notifications": True
}


@app.get("/api/settings")
async def get_settings():
    """Get application settings"""
    try:
        return {
            "success": True,
            "settings": app_settings
        }
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any]):
    """Update application settings"""
    try:
        app_settings.update(settings)
        
        logger.info(f"Updated settings: {list(settings.keys())}")
        
        return {
            "success": True,
            "settings": app_settings
        }
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can:
    - Receive workflow execution progress
    - Get notifications about new workflows
    - Receive system status updates
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back for now
            await manager.send_message({
                "type": "echo",
                "data": message,
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# Server Startup
# ============================================================================

def start_server(host: str = "127.0.0.1", port: int = 8765):
    """
    Start the FastAPI server.
    
    Args:
        host: Host to bind to (default: localhost only)
        port: Port to listen on (default: 8765)
    """
    import uvicorn
    
    logger.info(f"Starting CloneAI Desktop API Server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    start_server()
