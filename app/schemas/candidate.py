"""
Candidate schemas for request/response validation.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr


class CandidateCreate(BaseModel):
    """Schema for creating a new candidate"""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    interview_date: date
    resume_url: Optional[str] = None


class CandidateResponse(BaseModel):
    """Schema for candidate response data"""
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    interview_date: date
    candidate_status: str
    response_status: str
    followup_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CandidateUpdate(BaseModel):
    """Schema for updating candidate information"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    interview_date: Optional[date] = None
    resume_url: Optional[str] = None
    response_status: Optional[str] = None
    candidate_status: Optional[str] = None


class CandidateDashboard(BaseModel):
    """Schema for dashboard statistics"""
    total_candidates: int
    selected: int
    hired: int
    pending_responses: int
