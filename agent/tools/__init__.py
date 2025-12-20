"""
CloneAI Tools Package
Contains utility modules for various agent actions.
"""

from agent.skills.mail.client import (
    list_emails,
    create_draft_email,
    list_drafts_emails,
    send_email_now,
    send_draft_email,
    GmailClient
)
from .calendar import create_calendar_event, list_calendar_events, CalendarClient
from .documents import (
    merge_pdf_files,
    merge_ppt_files,
    convert_pdf_to_docx,
    convert_docx_to_pdf,
    convert_ppt_to_pdf,
    list_documents_in_directory,
    DocumentManager
)

__all__ = [
    'list_emails',
    'create_draft_email',
    'list_drafts_emails',
    'send_email_now',
    'send_draft_email',
    'GmailClient',
    'create_calendar_event',
    'list_calendar_events',
    'CalendarClient',
    'merge_pdf_files',
    'merge_ppt_files',
    'convert_pdf_to_docx',
    'convert_docx_to_pdf',
    'convert_ppt_to_pdf',
    'list_documents_in_directory',
    'DocumentManager'
]
