"""
Scheduler tool for CloneAI
Allows scheduling tasks to run at specific times daily.
"""

import os
import json
import schedule
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import subprocess
import sys

from agent.system_info import get_data_path

def get_scheduler_config_path() -> Path:
    """Get path to scheduler config file."""
    data_dir = get_data_path()
    return data_dir / 'scheduler_config.json'

def get_scheduler_log_path() -> Path:
    """Get path to scheduler log file."""
    data_dir = get_data_path()
    return data_dir / 'scheduler.log'

class TaskScheduler:
    """Manages scheduled tasks."""
    
    def __init__(self):
        self.config_path = get_scheduler_config_path()
        self.log_path = get_scheduler_log_path()
        self.tasks: List[Dict[str, Any]] = []
        self.load_tasks()
    
    def load_tasks(self):
        """Load tasks from config file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self.tasks = data.get('tasks', [])
    
    def save_tasks(self):
        """Save tasks to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({'tasks': self.tasks}, f, indent=2)
    
    def add_task(self, name: str, command: str, time: str, enabled: bool = True) -> Dict[str, Any]:
        """
        Add a scheduled task.
        
        Args:
            name: Task name/description
            command: Command to execute (e.g., "mail:list last 10")
            time: Time in HH:MM format (24-hour)
            enabled: Whether task is enabled
            
        Returns:
            Task dictionary
        """
        task = {
            'id': len(self.tasks) + 1,
            'name': name,
            'command': command,
            'time': time,
            'enabled': enabled,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'last_status': None
        }
        
        self.tasks.append(task)
        self.save_tasks()
        return task
    
    def remove_task(self, task_id: int) -> bool:
        """Remove a task by ID."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t['id'] != task_id]
        
        if len(self.tasks) < original_len:
            self.save_tasks()
            return True
        return False
    
    def toggle_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Enable/disable a task."""
        for task in self.tasks:
            if task['id'] == task_id:
                task['enabled'] = not task['enabled']
                self.save_tasks()
                return task
        return None
    
    def update_task_status(self, task_id: int, status: str):
        """Update task execution status."""
        for task in self.tasks:
            if task['id'] == task_id:
                task['last_run'] = datetime.now().isoformat()
                task['last_status'] = status
                self.save_tasks()
                break
    
    def get_tasks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all tasks or only enabled tasks."""
        if enabled_only:
            return [t for t in self.tasks if t.get('enabled', True)]
        return self.tasks
    
    def execute_task(self, task: Dict[str, Any]):
        """Execute a scheduled task."""
        task_id = task['id']
        command = task['command']
        
        try:
            # Log execution start
            self.log_execution(task_id, f"Starting execution: {command}")
            
            # Execute command using clai
            # Use subprocess to run clai command
            result = subprocess.run(
                [sys.executable, '-m', 'agent.cli', 'do', command],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            status = 'success' if result.returncode == 0 else 'failed'
            self.update_task_status(task_id, status)
            
            # Log execution result
            self.log_execution(
                task_id,
                f"Completed with status: {status}\nOutput: {result.stdout[:500]}"
            )
            
        except Exception as e:
            self.update_task_status(task_id, 'error')
            self.log_execution(task_id, f"Error: {str(e)}")
    
    def log_execution(self, task_id: int, message: str):
        """Log task execution."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] Task {task_id}: {message}\n"
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def schedule_all_tasks(self):
        """Schedule all enabled tasks."""
        schedule.clear()
        
        for task in self.get_tasks(enabled_only=True):
            task_time = task['time']
            schedule.every().day.at(task_time).do(self.execute_task, task)
    
    def run_scheduler(self):
        """Run the scheduler loop (blocking)."""
        self.schedule_all_tasks()
        
        print(f"Scheduler started with {len(self.get_tasks(enabled_only=True))} enabled task(s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped")


def add_scheduled_task(name: str, command: str, time: str) -> str:
    """
    Add a scheduled task.
    
    Args:
        name: Task name
        command: Command to execute
        time: Time in HH:MM format
        
    Returns:
        Success message
    """
    try:
        # Validate time format
        datetime.strptime(time, '%H:%M')
        
        scheduler = TaskScheduler()
        task = scheduler.add_task(name, command, time)
        
        output = []
        output.append("\n✅ Scheduled task added successfully!")
        output.append(f"\nTask ID: {task['id']}")
        output.append(f"Name: {task['name']}")
        output.append(f"Command: {task['command']}")
        output.append(f"Time: {task['time']} (daily)")
        output.append(f"Status: {'Enabled' if task['enabled'] else 'Disabled'}")
        output.append("\nNote: Run 'clai scheduler start' to activate the scheduler")
        
        return "\n".join(output)
    
    except ValueError:
        return "❌ Error: Invalid time format. Use HH:MM (e.g., 14:30)"
    except Exception as e:
        return f"❌ Error adding task: {str(e)}"


def list_scheduled_tasks() -> str:
    """List all scheduled tasks."""
    try:
        scheduler = TaskScheduler()
        tasks = scheduler.get_tasks()
        
        if not tasks:
            return "\n📋 No scheduled tasks found."
        
        output = []
        output.append(f"\n📋 Found {len(tasks)} scheduled task(s):\n")
        output.append("=" * 80)
        
        for task in tasks:
            status_icon = "✅" if task.get('enabled', True) else "❌"
            output.append(f"\n{status_icon} Task ID: {task['id']}")
            output.append(f"   Name: {task['name']}")
            output.append(f"   Command: {task['command']}")
            output.append(f"   Time: {task['time']} (daily)")
            output.append(f"   Status: {'Enabled' if task.get('enabled', True) else 'Disabled'}")
            
            if task.get('last_run'):
                output.append(f"   Last Run: {task['last_run']}")
                output.append(f"   Last Status: {task.get('last_status', 'N/A')}")
            
            output.append("-" * 80)
        
        return "\n".join(output)
    
    except Exception as e:
        return f"❌ Error listing tasks: {str(e)}"


def remove_scheduled_task(task_id: int) -> str:
    """Remove a scheduled task."""
    try:
        scheduler = TaskScheduler()
        
        if scheduler.remove_task(task_id):
            return f"\n✅ Task {task_id} removed successfully!"
        else:
            return f"\n❌ Task {task_id} not found."
    
    except Exception as e:
        return f"❌ Error removing task: {str(e)}"


def toggle_scheduled_task(task_id: int) -> str:
    """Enable/disable a scheduled task."""
    try:
        scheduler = TaskScheduler()
        task = scheduler.toggle_task(task_id)
        
        if task:
            status = "enabled" if task['enabled'] else "disabled"
            return f"\n✅ Task {task_id} {status} successfully!"
        else:
            return f"\n❌ Task {task_id} not found."
    
    except Exception as e:
        return f"❌ Error toggling task: {str(e)}"


def start_scheduler():
    """Start the scheduler daemon."""
    try:
        scheduler = TaskScheduler()
        scheduler.run_scheduler()
    except Exception as e:
        print(f"❌ Error starting scheduler: {str(e)}")
