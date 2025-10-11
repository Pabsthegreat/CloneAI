"""
Email management tool for CloneAI
Supports listing emails from Gmail with various filters.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailClient:
    """Gmail API client for reading emails."""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to credentials.json (from Google Cloud Console)
            token_path: Path to token.pickle (cached auth token)
        """
        self.credentials_path = credentials_path or os.path.join(
            str(Path.home()), '.clai', 'credentials.json'
        )
        self.token_path = token_path or os.path.join(
            str(Path.home()), '.clai', 'token.pickle'
        )
        self.service = None
        
    def authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}\n"
                        f"Please download credentials.json from Google Cloud Console:\n"
                        f"1. Go to https://console.cloud.google.com/\n"
                        f"2. Enable Gmail API\n"
                        f"3. Create OAuth 2.0 credentials\n"
                        f"4. Save as {self.credentials_path}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        return self.service
    
    def list_messages(
        self,
        max_results: int = 10,
        sender: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List messages from Gmail.
        
        Args:
            max_results: Maximum number of messages to retrieve
            sender: Filter by sender email address
            query: Custom Gmail query string
            
        Returns:
            List of message dictionaries with id, sender, subject, snippet, date
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Build query
            if sender and not query:
                query = f"from:{sender}"
            
            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Fetch full message details
            detailed_messages = []
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Extract headers
                headers = {
                    header['name']: header['value']
                    for header in msg_data['payload']['headers']
                }
                
                detailed_messages.append({
                    'id': msg_data['id'],
                    'from': headers.get('From', 'Unknown'),
                    'subject': headers.get('Subject', '(No subject)'),
                    'date': headers.get('Date', ''),
                    'snippet': msg_data.get('snippet', '')
                })
            
            return detailed_messages
            
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")


def format_email_list(messages: List[Dict[str, Any]]) -> str:
    """Format email list for display."""
    if not messages:
        return "No emails found."
    
    output = []
    output.append(f"\n📧 Found {len(messages)} email(s):\n")
    output.append("=" * 80)
    
    for i, msg in enumerate(messages, 1):
        output.append(f"\n{i}. From: {msg['from']}")
        output.append(f"   Subject: {msg['subject']}")
        output.append(f"   Date: {msg['date']}")
        output.append(f"   Preview: {msg['snippet'][:100]}...")
        output.append("-" * 80)
    
    return "\n".join(output)


def list_emails(count: int = 5, sender: Optional[str] = None) -> str:
    """
    List emails from Gmail.
    
    Args:
        count: Number of emails to list (default: 5)
        sender: Filter by sender email address (optional)
        
    Returns:
        Formatted string of email list
    """
    try:
        client = GmailClient()
        messages = client.list_messages(max_results=count, sender=sender)
        return format_email_list(messages)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error listing emails: {str(e)}"
