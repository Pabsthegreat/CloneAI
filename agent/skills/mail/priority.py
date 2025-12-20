"""
Priority email management for CloneAI
Manages high-priority email senders and filtering.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from agent.system_info import get_data_path

def get_priority_config_path() -> Path:
    """Get path to priority email config file."""
    data_dir = get_data_path()
    return data_dir / 'priority_emails.json'

class PriorityEmailManager:
    """Manages priority email senders and filtering."""
    
    def __init__(self):
        self.config_path = get_priority_config_path()
        self.priority_senders: List[str] = []
        self.priority_domains: List[str] = []
        self.load_config()
    
    def load_config(self):
        """Load priority email configuration."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self.priority_senders = data.get('senders', [])
                self.priority_domains = data.get('domains', [])
    
    def save_config(self):
        """Save priority email configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({
                'senders': self.priority_senders,
                'domains': self.priority_domains,
                'updated_at': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_priority_sender(self, email: str):
        """Add a priority sender email."""
        email = email.lower().strip()
        if email not in self.priority_senders:
            self.priority_senders.append(email)
            self.save_config()
    
    def add_priority_domain(self, domain: str):
        """Add a priority domain (e.g., @company.com)."""
        domain = domain.lower().strip()
        if not domain.startswith('@'):
            domain = '@' + domain
        if domain not in self.priority_domains:
            self.priority_domains.append(domain)
            self.save_config()
    
    def remove_priority_sender(self, email: str) -> bool:
        """Remove a priority sender."""
        email = email.lower().strip()
        if email in self.priority_senders:
            self.priority_senders.remove(email)
            self.save_config()
            return True
        return False
    
    def remove_priority_domain(self, domain: str) -> bool:
        """Remove a priority domain."""
        domain = domain.lower().strip()
        if not domain.startswith('@'):
            domain = '@' + domain
        if domain in self.priority_domains:
            self.priority_domains.remove(domain)
            self.save_config()
            return True
        return False
    
    def is_priority_email(self, from_email: str) -> bool:
        """
        Check if an email is from a priority sender.
        
        Args:
            from_email: Email address from "From" header
            
        Returns:
            True if email is from priority sender or domain
        """
        # Extract email from "Name <email@domain.com>" format
        import re
        match = re.search(r'<(.+?)>', from_email)
        if match:
            email = match.group(1)
        else:
            email = from_email
        
        email = email.lower().strip()
        
        # Check exact email match
        if email in self.priority_senders:
            return True
        
        # Check domain match
        for domain in self.priority_domains:
            if email.endswith(domain):
                return True
        
        return False
    
    def filter_priority_emails(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter emails to only priority ones.
        
        Args:
            emails: List of email dictionaries with 'from' key
            
        Returns:
            Filtered list of priority emails
        """
        return [email for email in emails if self.is_priority_email(email.get('from', ''))]
    
    def get_priority_list(self) -> Dict[str, Any]:
        """Get current priority configuration."""
        return {
            'senders': self.priority_senders,
            'domains': self.priority_domains,
            'total': len(self.priority_senders) + len(self.priority_domains)
        }


def add_priority_sender(identifier: str) -> str:
    """
    Add a priority sender or domain.
    
    Args:
        identifier: Email address or domain
        
    Returns:
        Success message
    """
    try:
        manager = PriorityEmailManager()
        
        # Determine if it's a domain or email
        if identifier.startswith('@') or ('@' not in identifier and '.' in identifier):
            # It's a domain
            manager.add_priority_domain(identifier)
            return f"\n✅ Priority domain added: {identifier}"
        else:
            # It's an email address
            manager.add_priority_sender(identifier)
            return f"\n✅ Priority sender added: {identifier}"
    
    except Exception as e:
        return f"❌ Error adding priority sender: {str(e)}"


def remove_priority_sender(identifier: str) -> str:
    """
    Remove a priority sender or domain.
    
    Args:
        identifier: Email address or domain
        
    Returns:
        Success message
    """
    try:
        manager = PriorityEmailManager()
        
        # Try both domain and email
        if manager.remove_priority_domain(identifier):
            return f"\n✅ Priority domain removed: {identifier}"
        elif manager.remove_priority_sender(identifier):
            return f"\n✅ Priority sender removed: {identifier}"
        else:
            return f"\n❌ Priority sender/domain not found: {identifier}"
    
    except Exception as e:
        return f"❌ Error removing priority sender: {str(e)}"


def list_priority_senders() -> str:
    """List all priority senders and domains."""
    try:
        manager = PriorityEmailManager()
        config = manager.get_priority_list()
        
        if config['total'] == 0:
            return "\n📧 No priority senders configured."
        
        output = []
        output.append(f"\n📧 Priority Email Configuration ({config['total']} total):\n")
        output.append("=" * 80)
        
        if config['senders']:
            output.append("\nPriority Senders:")
            for sender in config['senders']:
                output.append(f"  • {sender}")
        
        if config['domains']:
            output.append("\nPriority Domains:")
            for domain in config['domains']:
                output.append(f"  • {domain}")
        
        output.append("\n" + "=" * 80)
        output.append("\nUse these senders with: clai do \"mail:priority last 10\"")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"❌ Error listing priority senders: {str(e)}"


def get_priority_emails(count: int = 10, query: Optional[str] = None) -> str:
    """
    Get emails from priority senders.
    
    Args:
        count: Number of emails to retrieve
        query: Additional Gmail query filter
        
    Returns:
        Formatted email list
    """
    try:
        from .client import GmailClient, format_email_list
        
        manager = PriorityEmailManager()
        config = manager.get_priority_list()
        
        if config['total'] == 0:
            return "\n❌ No priority senders configured. Add some with: clai do \"mail:priority-add email@domain.com\""
        
        # Build Gmail query for priority senders
        sender_queries = []
        for sender in manager.priority_senders:
            sender_queries.append(f"from:{sender}")
        
        for domain in manager.priority_domains:
            sender_queries.append(f"from:{domain}")
        
        # Combine with OR
        priority_query = " OR ".join(sender_queries)
        
        # Add additional query if provided
        if query:
            priority_query = f"({priority_query}) AND ({query})"
        
        # Fetch emails
        client = GmailClient()
        messages = client.list_messages(max_results=count * 2, query=priority_query)
        
        # Limit to requested count
        messages = messages[:count]
        
        if not messages:
            return f"\n📧 No priority emails found (checked {config['total']} sender(s)/domain(s))"
        
        output = []
        output.append(f"\n📧 Found {len(messages)} priority email(s):\n")
        output.append("=" * 80)
        
        for i, msg in enumerate(messages, 1):
            output.append(f"\n{i}. From: {msg['from']}")
            output.append(f"   Subject: {msg['subject']}")
            output.append(f"   Date: {msg['date']}")
            output.append(f"   ID: {msg['id']}")
            output.append(f"   Preview: {msg['snippet'][:100]}...")
            output.append("-" * 80)
        
        return "\n".join(output)
    
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error getting priority emails: {str(e)}"
