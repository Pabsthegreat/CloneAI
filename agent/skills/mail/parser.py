"""
Email parsing tool for CloneAI
Extracts meeting information, dates, times, and links from emails.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import dateutil.parser
from urllib.parse import urlparse

class EmailParser:
    """Parse emails for meeting information."""
    
    # Meeting link patterns
    MEETING_PATTERNS = {
        'google_meet': r'https?://meet\.google\.com/[a-z\-]+',
        'zoom': r'https?://(?:[\w-]+\.)?zoom\.us/j/\d+(?:\?pwd=[A-Za-z0-9]+)?',
        'teams': r'https?://teams\.microsoft\.com/l/meetup-join/[^\s<>]+',
        'webex': r'https?://[\w-]+\.webex\.com/[\w-]+/j\.php\?[^\s<>]+',
        'meet': r'https?://meet\.[\w-]+\.com/[^\s<>]+',
        'generic_meeting': r'https?://(?:meeting|call|conference)\.[\w-]+\.com/[^\s<>]+'
    }
    
    # Date patterns
    DATE_PATTERNS = [
        # ISO format: 2025-10-15
        r'\b\d{4}-\d{2}-\d{2}\b',
        # US format: 10/15/2025, 10-15-2025
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
        # Month name: October 15, 2025 or Oct 15, 2025
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
        # Day Month Year: 15 October 2025
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b',
    ]
    
    # Time patterns
    TIME_PATTERNS = [
        # 14:30, 2:30
        r'\b\d{1,2}:\d{2}\b',
        # 2:30 PM, 14:30 PM
        r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',
        # 2 PM, 14:00
        r'\b\d{1,2}\s*(?:AM|PM|am|pm)\b',
    ]
    
    # Keywords that indicate a meeting
    MEETING_KEYWORDS = [
        'meeting', 'call', 'conference', 'discussion', 'sync', 'standup',
        'catch up', 'demo', 'presentation', 'interview', 'webinar',
        'session', 'appointment', 'scheduled', 'invite', 'invitation'
    ]
    
    def extract_meeting_links(self, text: str) -> List[Dict[str, str]]:
        """
        Extract meeting links from text.
        
        Args:
            text: Email body or subject text
            
        Returns:
            List of dictionaries with 'platform' and 'url'
        """
        links = []
        
        for platform, pattern in self.MEETING_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                url = match.group(0)
                # Clean up URL (remove trailing punctuation)
                url = re.sub(r'[.,;!?)\]}>]+$', '', url)
                links.append({
                    'platform': platform.replace('_', ' ').title(),
                    'url': url
                })
        
        # Deduplicate
        seen = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)
        
        return unique_links
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract potential dates from text."""
        dates = []
        
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(match.group(0))
        
        return dates
    
    def extract_times(self, text: str) -> List[str]:
        """Extract potential times from text."""
        times = []
        
        for pattern in self.TIME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                times.append(match.group(0))
        
        return times
    
    def parse_datetime(self, date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
        """
        Parse date and time strings into datetime object.
        
        Args:
            date_str: Date string
            time_str: Time string (optional)
            
        Returns:
            datetime object or None if parsing fails
        """
        try:
            # Combine date and time if both provided
            if time_str:
                combined = f"{date_str} {time_str}"
                return dateutil.parser.parse(combined, fuzzy=True)
            else:
                return dateutil.parser.parse(date_str, fuzzy=True)
        except Exception:
            return None
    
    def is_meeting_email(self, subject: str, body: str) -> bool:
        """
        Check if email is likely about a meeting.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if email contains meeting indicators
        """
        text = f"{subject} {body}".lower()
        
        # Check for meeting links
        if self.extract_meeting_links(text):
            return True
        
        # Check for meeting keywords
        for keyword in self.MEETING_KEYWORDS:
            if keyword in text:
                return True
        
        return False
    
    def extract_meeting_info(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Extract all meeting information from email.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            Dictionary with meeting details
        """
        text = f"{subject}\n{body}"
        
        # Extract components
        links = self.extract_meeting_links(text)
        dates = self.extract_dates(text)
        times = self.extract_times(text)
        
        # Try to parse datetime combinations
        datetimes = []
        if dates:
            for date in dates:
                if times:
                    for time in times:
                        dt = self.parse_datetime(date, time)
                        if dt:
                            datetimes.append(dt)
                else:
                    dt = self.parse_datetime(date)
                    if dt:
                        datetimes.append(dt)
        
        # Filter out past dates
        now = datetime.now()
        future_datetimes = [dt for dt in datetimes if dt > now]
        
        # Sort by date
        future_datetimes.sort()
        
        return {
            'is_meeting': self.is_meeting_email(subject, body),
            'meeting_links': links,
            'dates': dates,
            'times': times,
            'parsed_datetimes': [dt.isoformat() for dt in future_datetimes],
            'suggested_datetime': future_datetimes[0].isoformat() if future_datetimes else None,
            'suggested_link': links[0]['url'] if links else None
        }
    
    def extract_duration(self, text: str) -> int:
        """
        Extract meeting duration from text.
        
        Args:
            text: Email body or subject
            
        Returns:
            Duration in minutes (default: 60)
        """
        # Look for patterns like "30 minutes", "1 hour", "2hrs"
        duration_patterns = [
            (r'(\d+)\s*(?:minute|min|mins)', 1),  # minutes
            (r'(\d+)\s*(?:hour|hr|hrs)', 60),     # hours
            (r'(\d+)h\s*(\d+)m', None),           # 1h 30m format
        ]
        
        for pattern, multiplier in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if multiplier:
                    return int(match.group(1)) * multiplier
                else:
                    # Handle 1h 30m format
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    return hours * 60 + minutes
        
        # Default duration
        return 60


def parse_email_for_meetings(subject: str, body: str) -> Dict[str, Any]:
    """
    Parse email for meeting information.
    
    Args:
        subject: Email subject
        body: Email body
        
    Returns:
        Dictionary with meeting details
    """
    parser = EmailParser()
    return parser.extract_meeting_info(subject, body)
