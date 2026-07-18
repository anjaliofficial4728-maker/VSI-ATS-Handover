# app/models/email_log.py
"""
EmailLog model for database operations.
Represents an email sent to a candidate with all metadata.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class EmailLogCreate(BaseModel):
    """Schema for creating an email log entry"""
    candidate_id: str
    email_type: str
    recipient_email: str
    subject: str
    status: str = "pending"
    brevo_message_id: Optional[str] = None
    error_message: Optional[str] = None


class EmailLogUpdate(BaseModel):
    """Schema for updating an email log entry"""
    status: Optional[str] = None
    brevo_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EmailLogResponse(BaseModel):
    """Schema for returning email log data"""
    id: str
    candidate_id: str
    email_type: str
    recipient_email: str
    subject: str
    status: str
    brevo_message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailLogWithCandidate(EmailLogResponse):
    """Email log response with candidate info"""
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
