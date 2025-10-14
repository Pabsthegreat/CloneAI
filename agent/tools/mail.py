"""
Email management tool for CloneAI
Supports listing emails from Gmail with various filters.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import json

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
    
    def create_draft(self, to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None, attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a draft email in Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            attachments: List of file paths to attach (optional)
            
        Returns:
            Draft details dictionary
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
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {
                'id': draft['id'],
                'message_id': draft['message']['id'],
                'to': to,
                'subject': subject,
                'attachments': len(attachments) if attachments else 0
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
    
    def get_full_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get full message details including body.
        
        Args:
            message_id: The ID of the message
            
        Returns:
            Full message details
        """
        if not self.service:
            self.authenticate()
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            for header in message['payload']['headers']:
                headers[header['name']] = header['value']
            
            # Extract body
            body = self._get_message_body(message['payload'])
            
            return {
                'id': message['id'],
                'thread_id': message['threadId'],
                'from': headers.get('From', 'Unknown'),
                'to': headers.get('To', 'Unknown'),
                'subject': headers.get('Subject', '(No subject)'),
                'date': headers.get('Date', ''),
                'body': body,
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', [])
            }
        
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")
    
    def _get_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif 'parts' in part:
                    body += self._get_message_body(part)
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def download_attachments(self, message_id: str, save_dir: str) -> List[str]:
        """
        Download all attachments from an email.
        
        Args:
            message_id: The ID of the message
            save_dir: Directory to save attachments
            
        Returns:
            List of saved file paths
        """
        if not self.service:
            self.authenticate()
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            saved_files = []
            parts = message['payload'].get('parts', [])
            
            for part in parts:
                if part.get('filename'):
                    attachment_id = part['body'].get('attachmentId')
                    if attachment_id:
                        attachment = self.service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=attachment_id
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        filename = part['filename']
                        
                        # Create save directory
                        os.makedirs(save_dir, exist_ok=True)
                        
                        # Save file
                        filepath = os.path.join(save_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(file_data)
                        
                        saved_files.append(filepath)
            
            return saved_files
        
        except HttpError as error:
            raise Exception(f"Gmail API error: {error}")
    
    def list_messages_since(self, last_check: Optional[datetime] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        List messages since last check time.
        
        Args:
            last_check: Datetime of last check (default: 24 hours ago)
            max_results: Maximum messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        if not self.service:
            self.authenticate()
        
        if not last_check:
            last_check = datetime.now() - timedelta(days=1)
        
        # Convert to Gmail query format
        query = f"after:{int(last_check.timestamp())}"
        
        return self.list_messages(max_results=max_results, query=query)
    
    def create_meeting_email(
        self,
        to: str,
        subject: str,
        meeting_time: str,
        duration: int,
        meeting_link: Optional[str] = None,
        additional_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and send a meeting invitation email.
        
        Args:
            to: Recipient email
            subject: Meeting subject
            meeting_time: Meeting time (ISO format or readable)
            duration: Duration in minutes
            meeting_link: Meeting link (Google Meet, Zoom, etc.)
            additional_body: Additional message body
            
        Returns:
            Sent email details
        """
        # Build email body
        body_parts = []
        body_parts.append(f"Subject: {subject}")
        body_parts.append(f"\nTime: {meeting_time}")
        body_parts.append(f"Duration: {duration} minutes")
        
        if meeting_link:
            body_parts.append(f"\nJoin Meeting: {meeting_link}")
        
        if additional_body:
            body_parts.append(f"\n{additional_body}")
        
        body_parts.append("\n\nLooking forward to connecting with you!")
        
        body = "\n".join(body_parts)
        
        return self.send_email(to=to, subject=f"Meeting Invitation: {subject}", body=body)


def format_email_list(messages: List[Dict[str, Any]]) -> str:
    """Format email list for display."""
    if not messages:
        return "No emails found."
    
    output = []
    output.append(f"\n📧 Found {len(messages)} email(s):\n")
    output.append("=" * 80)
    
    for i, msg in enumerate(messages, 1):
        output.append(f"\n{i}. Message ID: {msg['id']}") 
        output.append(f"   From: {msg['from']}")
        output.append(f"   Subject: {msg['subject']}")
        output.append(f"   Date: {msg['date']}")
        output.append(f"   Preview: {msg['snippet'][:100]}...")
        output.append("-" * 80)
    
    return "\n".join(output)


def get_email_messages(
    count: int = 5,
    sender: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve raw email message metadata with graceful fallbacks for sender matching.

    Attempts, in order:
        1. Provided query/sender parameters.
        2. Gmail `from:` search using the sender string.
        3. If sender contains '@', try domain and local-part separately.
        4. If sender lacks '@', treat it directly as a substring query.
    """
    client = GmailClient()

    attempts: List[Tuple[Optional[str], Optional[str]]] = []
    seen: set[Tuple[str, str]] = set()

    def add_attempt(attempt_sender: Optional[str], attempt_query: Optional[str]) -> None:
        key = (attempt_sender or "", attempt_query or "")
        if key not in seen:
            seen.add(key)
            attempts.append((attempt_sender, attempt_query))

    if query:
        add_attempt(None, query)
    else:
        add_attempt(sender, None)
        if sender:
            normalized = sender.strip()
            add_attempt(None, f"from:{normalized}")
            if "@" in normalized:
                local_part, _, domain = normalized.partition("@")
                if domain:
                    add_attempt(None, f"from:{domain}")
                if local_part:
                    add_attempt(None, f"from:{local_part}")
            else:
                add_attempt(None, f"from:{normalized}")

    if not attempts:
        add_attempt(None, None)

    last_messages: List[Dict[str, Any]] = []

    for attempt_sender, attempt_query in attempts:
        messages = client.list_messages(
            max_results=count,
            sender=attempt_sender,
            query=attempt_query,
        )
        if messages:
            return messages
        last_messages = messages

    return last_messages


def list_emails(
    count: int = 5,
    sender: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """
    List emails from Gmail.
    
    Args:
        count: Number of emails to list (default: 5)
        sender: Filter by sender email address (optional)
        query: Additional Gmail query string (optional)
        
    Returns:
        Formatted string of email list
    """
    try:
        messages = get_email_messages(count=count, sender=sender, query=query)
        return format_email_list(messages)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error listing emails: {str(e)}"


def create_draft_email(to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None, attachments: Optional[List[str]] = None) -> str:
    """
    Create a draft email in Gmail.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        attachments: List of file paths to attach (optional)
        
    Returns:
        Success message with draft details
    """
    try:
        client = GmailClient()
        draft = client.create_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc, attachments=attachments)
        
        output = []
        output.append("\n✅ Draft created successfully!")
        output.append(f"\nDraft ID: {draft['id']}")
        output.append(f"To: {draft['to']}")
        output.append(f"Subject: {draft['subject']}")
        if attachments:
            output.append(f"Attachments: {len(attachments)} file(s)")
            for att in attachments:
                output.append(f"  - {os.path.basename(att)}")
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


def get_full_email(message_id: str) -> str:
    """
    Get full email body and details.
    
    Args:
        message_id: Email message ID
        
    Returns:
        Formatted email details
    """
    try:
        client = GmailClient()
        message = client.get_full_message(message_id)
        
        output = []
        output.append("\n" + "=" * 80)
        output.append(f"From: {message['from']}")
        output.append(f"To: {message['to']}")
        output.append(f"Subject: {message['subject']}")
        output.append(f"Date: {message['date']}")
        output.append("=" * 80)
        output.append("\nBody:")
        output.append("-" * 80)
        output.append(message['body'])
        output.append("-" * 80)
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error getting email: {str(e)}"


def download_email_attachments(message_id: str, save_dir: Optional[str] = None) -> str:
    """
    Download attachments from an email.
    
    Args:
        message_id: Email message ID
        save_dir: Directory to save (default: Downloads/CloneAI_Attachments)
        
    Returns:
        Success message with file list
    """
    try:
        if not save_dir:
            save_dir = str(Path.home() / "Downloads" / "CloneAI_Attachments")
        
        client = GmailClient()
        files = client.download_attachments(message_id, save_dir)
        
        if not files:
            return f"\n📎 No attachments found in email {message_id}"
        
        output = []
        output.append(f"\n✅ Downloaded {len(files)} attachment(s):")
        output.append(f"\nSaved to: {save_dir}\n")
        
        for i, filepath in enumerate(files, 1):
            filename = os.path.basename(filepath)
            output.append(f"{i}. {filename}")
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error downloading attachments: {str(e)}"


def scan_emails_for_meetings(hours_back: int = 24, auto_add: bool = True) -> str:
    """
    Scan recent emails for meeting information and optionally auto-add to calendar.
    
    Args:
        hours_back: How many hours back to scan (default: 24)
        auto_add: Automatically add detected meetings to calendar (default: True)
        
    Returns:
        Formatted list of detected meetings
    """
    try:
        from agent.tools.email_parser import EmailParser
        from agent.tools.calendar import CalendarClient
        
        client = GmailClient()
        parser = EmailParser()
        
        # Get emails from last N hours
        last_check = datetime.now() - timedelta(hours=hours_back)
        messages = client.list_messages_since(last_check, max_results=50)
        
        if not messages:
            return f"\n📧 No emails found in the last {hours_back} hours."
        
        # Scan for meetings
        meetings_found = []
        for msg in messages:
            # Get full body
            full_msg = client.get_full_message(msg['id'])
            meeting_info = parser.extract_meeting_info(full_msg['subject'], full_msg['body'])
            
            # Accept meetings with either datetime or meeting link
            has_datetime = meeting_info['suggested_datetime'] is not None
            has_link = meeting_info['suggested_link'] is not None
            
            if meeting_info['is_meeting'] and ((has_datetime and has_link) or (has_link)):
                meetings_found.append({
                    'email_id': msg['id'],
                    'from': msg['from'],
                    'subject': full_msg['subject'],
                    'meeting_info': meeting_info
                })
        
        if not meetings_found:
            return f"\n📅 No meeting invitations detected in the last {hours_back} hours."
        
        output = []
        output.append(f"\n📅 Found {len(meetings_found)} meeting(s) in emails:\n")
        output.append("=" * 80)
        
        # Auto-add to calendar if enabled
        calendar_client = None
        added_count = 0
        
        if auto_add:
            try:
                calendar_client = CalendarClient()
            except Exception as e:
                output.append(f"\n⚠️  Warning: Could not connect to Calendar API: {str(e)}")
                output.append("Meetings will be listed but not added to calendar.\n")
        
        for i, meeting in enumerate(meetings_found, 1):
            info = meeting['meeting_info']
            output.append(f"\n{i}. {meeting['subject']}")
            output.append(f"   From: {meeting['from']}")
            output.append(f"   Suggested Time: {info['suggested_datetime']}")
            if info['suggested_link']:
                output.append(f"   Meeting Link: {info['suggested_link']}")
            output.append(f"   Email ID: {meeting['email_id']}")
            
            # Auto-add to calendar
            if auto_add and calendar_client:
                try:
                    event = calendar_client.create_event(
                        summary=meeting['subject'],
                        start_time=info['suggested_datetime'],
                        duration_minutes=info.get('duration', 60),
                        description=f"From: {meeting['from']}\nMeeting Link: {info.get('suggested_link', 'N/A')}"
                    )
                    output.append(f"   ✅ Added to calendar: {event.get('html_link', '')}")
                    added_count += 1
                except Exception as e:
                    output.append(f"   ❌ Failed to add to calendar: {str(e)}")
            
            output.append("-" * 80)
        
        if auto_add and added_count > 0:
            output.append(f"\n✅ Successfully added {added_count}/{len(meetings_found)} meeting(s) to your calendar!")
        elif not auto_add:
            output.append("\nUse: clai do \"mail:add-meeting email-id:MESSAGE_ID\" to add to calendar")
        
        return "\n".join(output)
    
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error scanning emails: {str(e)}"


def add_meeting_from_email(message_id: str, custom_time: Optional[str] = None) -> str:
    """
    Extract meeting from email and add to calendar.
    
    Args:
        message_id: Email message ID
        custom_time: Override detected time (optional)
        
    Returns:
        Success message
    """
    try:
        from agent.tools.email_parser import EmailParser
        from agent.tools.calendar import CalendarClient
        
        email_client = GmailClient()
        parser = EmailParser()
        calendar_client = CalendarClient()
        
        # Get full email
        message = email_client.get_full_message(message_id)
        
        # Parse meeting info
        meeting_info = parser.extract_meeting_info(message['subject'], message['body'])
        
        if not meeting_info['is_meeting']:
            return f"\n❌ No meeting information detected in email."
        
        # Determine meeting time
        if custom_time:
            meeting_time = custom_time
        elif meeting_info['suggested_datetime']:
            meeting_time = meeting_info['suggested_datetime']
        else:
            return f"\n❌ Could not determine meeting time. Use custom_time parameter."
        
        # Extract duration
        duration = parser.extract_duration(message['body'])
        
        # Create calendar event
        description_parts = [f"Email from: {message['from']}"]
        if meeting_info['suggested_link']:
            description_parts.append(f"\nMeeting Link: {meeting_info['suggested_link']}")
        description_parts.append(f"\n\nOriginal Email:\n{message['snippet']}")
        
        event = calendar_client.create_event(
            summary=message['subject'],
            start_time=meeting_time,
            duration_minutes=duration,
            description="\n".join(description_parts),
            location=meeting_info['suggested_link'] if meeting_info['suggested_link'] else None
        )
        
        output = []
        output.append("\n✅ Meeting added to calendar!")
        output.append(f"\nTitle: {event['summary']}")
        output.append(f"Time: {event['start']}")
        output.append(f"Duration: {duration} minutes")
        if meeting_info['suggested_link']:
            output.append(f"Link: {meeting_info['suggested_link']}")
        
        return "\n".join(output)
    
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error adding meeting: {str(e)}"


def create_and_send_meeting_invite(
    to: str,
    subject: str,
    time: str,
    duration: int = 60,
    platform: str = 'gmeet',
    message: Optional[str] = None
) -> str:
    """
    Create meeting and send invitation email.
    
    Args:
        to: Recipient email
        subject: Meeting subject
        time: Meeting time (ISO format)
        duration: Duration in minutes
        platform: Meeting platform (gmeet, zoom, teams, custom)
        message: Additional message
        
    Returns:
        Success message
    """
    try:
        from agent.tools.calendar import CalendarClient
        import uuid
        
        meeting_link = None
        calendar_event = None
        
        # Generate meeting link based on platform
        if platform.lower() == 'gmeet':
            # For Google Meet, create a real calendar event with Google Meet link
            calendar_client = CalendarClient()
            
            # Create event with Google Meet
            calendar_event = calendar_client.create_event(
                summary=subject,
                start_time=time,
                duration_minutes=duration,
                description=message,
                attendees=[to],
                add_google_meet=True
            )
            
            # Extract the Meet link from the created event
            meeting_link = calendar_event.get('meet_link')
            
            if not meeting_link:
                # Fallback if Meet link not found
                meeting_link = f"https://meet.google.com/{uuid.uuid4().hex[:10]}"
            
        elif platform.lower() == 'custom':
            meeting_link = message  # Use message as custom link
        else:
            meeting_link = f"https://{platform}.com/meeting"  # Generic placeholder
        
        # Send invitation email
        email_client = GmailClient()
        result = email_client.create_meeting_email(
            to=to,
            subject=subject,
            meeting_time=time,
            duration=duration,
            meeting_link=meeting_link,
            additional_body=message
        )
        
        output = []
        output.append("\n✅ Meeting invitation sent!")
        output.append(f"\nTo: {to}")
        output.append(f"Subject: {subject}")
        output.append(f"Time: {time}")
        output.append(f"Duration: {duration} minutes")
        output.append(f"Link: {meeting_link}")
        
        if calendar_event:
            output.append(f"\n📅 Calendar event created: {calendar_event.get('html_link', 'N/A')}")
            output.append("✅ Attendee will receive calendar invitation with Google Meet link")
        
        return "\n".join(output)
    
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating meeting invite: {str(e)}"
