# app/routers/candidates.py
"""
Candidate management routes.
Updated for Phase 1 - removed send-email, use emails router instead.
"""

from fastapi import APIRouter
from app.schemas.candidate import (
    CandidateCreate,
    CandidateUpdate,
)

from app.services.candidate_service import CandidateService

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"]
)


@router.post("/")
def create_candidate(candidate: CandidateCreate):
    """Create a new candidate"""
    return CandidateService.create_candidate(candidate)


@router.get("/dashboard")
def get_dashboard_stats():
    """Get dashboard statistics"""
    return CandidateService.get_dashboard_stats()


@router.get("/")
def get_all_candidates():
    """Get all candidates"""
    return CandidateService.get_all_candidates()


@router.get("/{candidate_id}")
def get_candidate_by_id(candidate_id: str):
    """Get candidate by ID"""
    return CandidateService.get_candidate_by_id(candidate_id)


@router.put("/{candidate_id}")
def update_candidate(candidate_id: str, candidate: CandidateUpdate):
    """Update candidate information"""
    return CandidateService.update_candidate(candidate_id, candidate)


@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: str):
    """Delete a candidate"""
    return CandidateService.delete_candidate(candidate_id)


# NOTE: /send-email endpoint moved to /api/emails/send in emails.py router
# This maintains the separation of concerns:
# - Candidate routes: CRUD operations
# - Email routes: Email sending and logs
