# app/services/candidate_service.py
"""
Candidate service for managing candidates.
Updated for Phase 1 - email sending moved to EmailService.
"""

from datetime import datetime
from app.database import supabase


class CandidateService:
    """Service for candidate management operations"""

    @staticmethod
    def create_candidate(candidate):
        """
        Create a new candidate.
        
        Args:
            candidate: CandidateCreate schema
        
        Returns:
            Created candidate data
        """
        data = {
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "resume_url": candidate.resume_url,
            "interview_date": str(candidate.interview_date),
            "response_status": "not_sent",
            "candidate_status": "applied",
            "followup_count": 0,
            "initial_email_sent_at": None,
            "last_followup_sent_at": None,
            "updated_at": datetime.utcnow().isoformat()
        }

        response = (
            supabase
            .table("candidates")
            .insert(data)
            .execute()
        )

        return response.data

    @staticmethod
    def get_all_candidates():
        """
        Get all candidates.
        
        Returns:
            List of all candidates
        """
        response = (
            supabase
            .table("candidates")
            .select("*")
            .execute()
        )

        return response.data

    @staticmethod
    def get_candidate_by_id(candidate_id: str):
        """
        Get candidate by ID.
        
        Args:
            candidate_id: UUID of candidate
        
        Returns:
            Candidate data or empty list if not found
        """
        response = (
            supabase
            .table("candidates")
            .select("*")
            .eq("id", candidate_id)
            .execute()
        )

        return response.data

    @staticmethod
    def update_candidate(candidate_id: str, candidate):
        """
        Update candidate information.
        
        Args:
            candidate_id: UUID of candidate
            candidate: CandidateUpdate schema
        
        Returns:
            Updated candidate data
        """
        update_data = candidate.model_dump(exclude_unset=True)

        if "interview_date" in update_data:
            update_data["interview_date"] = str(update_data["interview_date"])

        update_data["updated_at"] = datetime.utcnow().isoformat()

        response = (
            supabase
            .table("candidates")
            .update(update_data)
            .eq("id", candidate_id)
            .execute()
        )

        return response.data

    @staticmethod
    def delete_candidate(candidate_id: str):
        """
        Delete a candidate.
        
        Args:
            candidate_id: UUID of candidate
        
        Returns:
            Deleted candidate data
        """
        response = (
            supabase
            .table("candidates")
            .delete()
            .eq("id", candidate_id)
            .execute()
        )

        return response.data

    @staticmethod
    def get_dashboard_stats():
        """
        Get dashboard statistics.
        
        Returns:
            Dictionary with candidate counts by status
        """
        response = (
            supabase
            .table("candidates")
            .select("*")
            .execute()
        )

        candidates = response.data

        total_candidates = len(candidates)

        selected = len([
            c for c in candidates
            if c["candidate_status"] == "selected"
        ])

        hired = len([
            c for c in candidates
            if c["candidate_status"] == "hired"
        ])

        pending_responses = len([
            c for c in candidates
            if c["response_status"] == "pending"
        ])

        return {
            "total_candidates": total_candidates,
            "selected": selected,
            "hired": hired,
            "pending_responses": pending_responses,
        }
