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
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

from agent.system_info import get_credentials_path, get_gmail_token_path

# Gmail API scopes - includes reading, composing, and sending
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send'
]

class GmailClient:
    """Gmail API client for reading emails."""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to credentials.json (from Google Cloud Console)
            token_path: Path to token.pickle (cached auth token)
        """
        self.credentials_path = credentials_path or str(get_credentials_path())
        self.token_path = token_path or str(get_gmail_token_path())
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
    
    def create_draft(self, to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a draft email in Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            
        Returns:
            Draft details dictionary
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {
                'id': draft['id'],
                'message_id': draft['message']['id'],
                'to': to,
                'subject': subject
            }
            
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")
    
    def list_drafts(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List draft emails from Gmail.
        
        Args:
            max_results: Maximum number of drafts to retrieve
            
        Returns:
            List of draft dictionaries with details
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Get draft list
            results = self.service.users().drafts().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            drafts = results.get('drafts', [])
            
            if not drafts:
                return []
            
            # Fetch full draft details
            detailed_drafts = []
            for draft in drafts:
                draft_data = self.service.users().drafts().get(
                    userId='me',
                    id=draft['id'],
                    format='metadata',
                    metadataHeaders=['To', 'Subject', 'Date']
                ).execute()
                
                # Extract headers
                headers = {
                    header['name']: header['value']
                    for header in draft_data['message']['payload']['headers']
                }
                
                detailed_drafts.append({
                    'id': draft_data['id'],
                    'message_id': draft_data['message']['id'],
                    'to': headers.get('To', 'Unknown'),
                    'subject': headers.get('Subject', '(No subject)'),
                    'date': headers.get('Date', ''),
                    'snippet': draft_data['message'].get('snippet', '')
                })
            
            return detailed_drafts
            
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email directly (not as draft).
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            attachments: List of file paths to attach (optional)
            
        Returns:
            Sent message details
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Create message with or without attachments
            if attachments:
                message = MIMEMultipart()
            else:
                message = MIMEText(body)
            
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body if using multipart
            if attachments:
                message.attach(MIMEText(body, 'plain'))
                
                # Add attachments
                for file_path in attachments:
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"Attachment not found: {file_path}")
                    
                    # Guess the content type
                    content_type, _ = mimetypes.guess_type(file_path)
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    
                    main_type, sub_type = content_type.split('/', 1)
                    
                    with open(file_path, 'rb') as f:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(f.read())
                    
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(file_path)}'
                    )
                    message.attach(attachment)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            sent = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'id': sent['id'],
                'to': to,
                'subject': subject,
                'attachments': len(attachments) if attachments else 0
            }
            
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")
    
    def send_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Send an existing draft by ID.
        
        Args:
            draft_id: The ID of the draft to send
            
        Returns:
            Sent message details
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Send draft
            sent = self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            return {
                'id': sent['id'],
                'draft_id': draft_id
            }
            
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


def create_draft_email(to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None) -> str:
    """
    Create a draft email in Gmail.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        
    Returns:
        Success message with draft details
    """
    try:
        client = GmailClient()
        draft = client.create_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        
        output = []
        output.append("\n✅ Draft created successfully!")
        output.append(f"\nDraft ID: {draft['id']}")
        output.append(f"To: {draft['to']}")
        output.append(f"Subject: {draft['subject']}")
        output.append("\nYou can find this draft in your Gmail drafts folder.")
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating draft: {str(e)}"


def list_drafts_emails(count: int = 10) -> str:
    """
    List draft emails from Gmail.
    
    Args:
        count: Number of drafts to list (default: 10)
        
    Returns:
        Formatted string of draft list
    """
    try:
        client = GmailClient()
        drafts = client.list_drafts(max_results=count)
        
        if not drafts:
            return "\n📧 No drafts found."
        
        output = []
        output.append(f"\n📝 Found {len(drafts)} draft(s):\n")
        output.append("=" * 80)
        
        for i, draft in enumerate(drafts, 1):
            output.append(f"\n{i}. Draft ID: {draft['id']}")
            output.append(f"   To: {draft['to']}")
            output.append(f"   Subject: {draft['subject']}")
            output.append(f"   Preview: {draft['snippet'][:100]}...")
            output.append("-" * 80)
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error listing drafts: {str(e)}"


def send_email_now(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments: Optional[List[str]] = None
) -> str:
    """
    Send an email directly (not as draft).
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        attachments: List of file paths to attach (optional)
        
    Returns:
        Success message with sent email details
    """
    try:
        client = GmailClient()
        result = client.send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            attachments=attachments
        )
        
        output = []
        output.append("\n✅ Email sent successfully!")
        output.append(f"\nMessage ID: {result['id']}")
        output.append(f"To: {result['to']}")
        output.append(f"Subject: {result['subject']}")
        if result['attachments'] > 0:
            output.append(f"Attachments: {result['attachments']} file(s)")
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


def send_draft_email(draft_id: str) -> str:
    """
    Send an existing draft by ID.
    
    Args:
        draft_id: The ID of the draft to send
        
    Returns:
        Success message
    """
    try:
        client = GmailClient()
        result = client.send_draft(draft_id=draft_id)
        
        output = []
        output.append("\n✅ Draft sent successfully!")
        output.append(f"\nMessage ID: {result['id']}")
        output.append(f"Draft ID: {result['draft_id']}")
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error sending draft: {str(e)}"
