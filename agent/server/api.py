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
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# CloneAI imports
from agent.cli import execute_single_command
from agent.tools.tiered_planner import classify_request, plan_step_execution, WorkflowMemory
from agent.workflows import registry as workflow_registry

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
        
        workflows = workflow_registry.list()
        
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
        result = execute_single_command(req.command, extras=req.extras)
        
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
        
        # Use tiered planner to classify request
        classification = classify_request(req.message)
        
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
        
        # Classify request
        classification = classify_request(req.message)
        
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
                            execution_plan = plan_step_execution(
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
                            
                            # Execute the CLI command
                            step_output = execute_single_command(command_to_run)
                            
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
                            logger.error(f"   ✗ Step {step_index} failed: {step_error}", exc_info=True)
                            response["steps_executed"].append({
                                "step": step_index,
                                "description": step_instruction,
                                "status": "failed",
                                "error": str(step_error)
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
                    # For mail commands, convert natural language to CLI format
                    if "mail" in classification.categories:
                        # Extract number from message (e.g., "last 5 emails" -> 5)
                        import re
                        numbers = re.findall(r'\d+', req.message)
                        count = int(numbers[0]) if numbers else 10
                        
                        # Build command
                        if "unread" in req.message.lower():
                            command = f"mail:list last {count} unread"
                        else:
                            command = f"mail:list last {count}"
                        
                        logger.info(f"Executing mail command: {command}")
                        result = execute_single_command(command)
                        response["executed"] = True
                        response["output"] = result
                    
                    elif "calendar" in classification.categories:
                        # Extract number for calendar events
                        import re
                        numbers = re.findall(r'\d+', req.message)
                        count = int(numbers[0]) if numbers else 10
                        command = f"calendar:list count:{count}"
                        
                        logger.info(f"Executing calendar command: {command}")
                        result = execute_single_command(command)
                        response["executed"] = True
                        response["output"] = result
                    
                    else:
                        # Try direct execution with natural language
                        logger.info(f"Attempting direct execution: {req.message}")
                        result = execute_single_command(req.message)
                        response["executed"] = True
                        response["output"] = result
                        
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

@app.get("/api/workflows")
async def list_workflows():
    """List all available workflows (built-in + custom)"""
    try:
        workflows = workflow_registry.list()
        
        workflow_list = []
        for spec in workflows:
            workflow_list.append({
                "namespace": spec.namespace,
                "name": spec.name,  # Fixed: WorkflowSpec uses 'name' not 'action'
                "summary": spec.summary,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type.__name__ if hasattr(p.type, '__name__') else str(p.type),
                        "required": p.required,
                        "description": p.description,
                        "default": p.default
                    }
                    for p in spec.parameters
                ],
                "usage": spec.metadata.get('usage', None) if spec.metadata else None
            })
        
        # Separate built-in from custom
        custom_dir = Path.home() / ".clai" / "workflows" / "custom"
        custom_workflows = []
        if custom_dir.exists():
            for py_file in custom_dir.glob("*.py"):
                custom_workflows.append({
                    "filename": py_file.name,
                    "path": str(py_file),
                    "modified": datetime.fromtimestamp(py_file.stat().st_mtime).isoformat()
                })
        
        return {
            "success": True,
            "total": len(workflow_list),
            "workflows": workflow_list,
            "custom_workflows": custom_workflows,
            "custom_count": len(custom_workflows)
        }
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/reload")
async def reload_workflows():
    """Reload workflow registry (picks up new custom workflows)"""
    try:
        logger.info("Reloading workflow registry...")
        importlib.reload(workflow_registry)
        
        workflows = workflow_registry.list()
        
        return {
            "success": True,
            "workflows_count": len(workflows),
            "message": "Workflow registry reloaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to reload workflows: {e}")
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
