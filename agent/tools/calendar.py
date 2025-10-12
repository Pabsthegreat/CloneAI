"""
Google Calendar management tool for CloneAI
Supports creating and listing calendar events.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import dateutil.parser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agent.system_info import get_credentials_path, get_calendar_token_path

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarClient:
    """Google Calendar API client."""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Calendar client.
        
        Args:
            credentials_path: Path to credentials.json (from Google Cloud Console)
            token_path: Path to token_calendar.pickle (cached auth token)
        """
        self.credentials_path = credentials_path or str(get_credentials_path())
        self.token_path = token_path or str(get_calendar_token_path())
        self.service = None
        
    def authenticate(self):
        """Authenticate with Google Calendar API."""
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
                        f"2. Enable Google Calendar API\n"
                        f"3. Create OAuth 2.0 credentials (Desktop app)\n"
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
        
        self.service = build('calendar', 'v3', credentials=creds)
        return self.service
    
    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            summary: Event title
            start_time: Start time (ISO format or natural language)
            end_time: End time (ISO format or natural language, optional)
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendee email addresses (optional)
            duration_minutes: Duration in minutes if end_time not provided (default: 60)
            
        Returns:
            Event details dictionary
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Parse start time
            if isinstance(start_time, str):
                start_dt = dateutil.parser.parse(start_time)
            else:
                start_dt = start_time
            
            # Calculate end time if not provided
            if end_time:
                if isinstance(end_time, str):
                    end_dt = dateutil.parser.parse(end_time)
                else:
                    end_dt = end_time
            else:
                end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            # Build event
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            if description:
                event['description'] = description
            
            if location:
                event['location'] = location
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Create event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return {
                'id': created_event['id'],
                'summary': created_event['summary'],
                'start': created_event['start'].get('dateTime', created_event['start'].get('date')),
                'end': created_event['end'].get('dateTime', created_event['end'].get('date')),
                'html_link': created_event.get('htmlLink', '')
            }
            
        except HttpError as error:
            raise Exception(f"Calendar API error: {error}")
        except Exception as e:
            raise Exception(f"Error parsing date/time: {e}")
    
    def list_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        List upcoming calendar events.
        
        Args:
            max_results: Maximum number of events to retrieve
            time_min: Start of time range (default: now)
            time_max: End of time range (optional)
            
        Returns:
            List of event dictionaries
        """
        if not self.service:
            self.authenticate()
        
        try:
            # Default to now if not specified
            if not time_min:
                time_min = datetime.utcnow()
            
            # Build parameters
            params = {
                'calendarId': 'primary',
                'timeMin': time_min.isoformat() + 'Z',
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if time_max:
                params['timeMax'] = time_max.isoformat() + 'Z'
            
            # Get events
            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', '(No title)'),
                    'start': start,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return formatted_events
            
        except HttpError as error:
            raise Exception(f"Calendar API error: {error}")


def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    duration_minutes: int = 60
) -> str:
    """
    Create a Google Calendar event.
    
    Args:
        summary: Event title
        start_time: Start time (ISO format or natural language)
        end_time: End time (optional)
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee emails (optional)
        duration_minutes: Duration in minutes if end_time not provided
        
    Returns:
        Success message with event details
    """
    try:
        client = CalendarClient()
        event = client.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
            duration_minutes=duration_minutes
        )
        
        output = []
        output.append("\n✅ Calendar event created successfully!")
        output.append(f"\nEvent ID: {event['id']}")
        output.append(f"Title: {event['summary']}")
        output.append(f"Start: {event['start']}")
        output.append(f"End: {event['end']}")
        if event.get('html_link'):
            output.append(f"Link: {event['html_link']}")
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating calendar event: {str(e)}"


def list_calendar_events(count: int = 10) -> str:
    """
    List upcoming calendar events.
    
    Args:
        count: Number of events to list (default: 10)
        
    Returns:
        Formatted string of event list
    """
    try:
        client = CalendarClient()
        events = client.list_events(max_results=count)
        
        if not events:
            return "\n📅 No upcoming events found."
        
        output = []
        output.append(f"\n📅 Found {len(events)} upcoming event(s):\n")
        output.append("=" * 80)
        
        for i, event in enumerate(events, 1):
            output.append(f"\n{i}. {event['summary']}")
            output.append(f"   Start: {event['start']}")
            if event.get('location'):
                output.append(f"   Location: {event['location']}")
            if event.get('description'):
                output.append(f"   Description: {event['description'][:100]}...")
            output.append("-" * 80)
        
        return "\n".join(output)
    except FileNotFoundError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        return f"❌ Error listing events: {str(e)}"
