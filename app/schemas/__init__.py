"""
Pydantic schemas for request/response validation.
"""

from app.schemas.candidate import (
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
    CandidateDashboard,
)
from app.schemas.email import (
    SendEmailRequest,
    SendEmailResponse,
    EmailTypeDefinition,
    EmailTypesListResponse,
)

__all__ = [
    # Candidate schemas
    "CandidateCreate",
    "CandidateResponse",
    "CandidateUpdate",
    "CandidateDashboard",
    # Email schemas
    "SendEmailRequest",
    "SendEmailResponse",
    "EmailTypeDefinition",
    "EmailTypesListResponse",
]
