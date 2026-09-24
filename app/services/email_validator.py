# # app/services/email_validator.py
# """
# Email validation service.
# Validates email type against candidate status and other rules.
# """

# from app.config import EMAIL_TYPES, VALID_CANDIDATE_STATUSES


# class EmailValidator:
#     """Validates email sending requests"""
    
#     @staticmethod
#     def is_valid_email_type(email_type: str) -> bool:
#         """
#         Check if email type is defined.
        
#         Args:
#             email_type: Email type to validate
        
#         Returns:
#             True if email type exists in EMAIL_TYPES
#         """
#         return email_type in EMAIL_TYPES
    
#     @staticmethod
#     def is_valid_candidate_status(candidate_status: str) -> bool:
#         """
#         Check if candidate status is valid.
        
#         Args:
#             candidate_status: Candidate status to validate
        
#         Returns:
#             True if status is in VALID_CANDIDATE_STATUSES
#         """
#         return candidate_status in VALID_CANDIDATE_STATUSES
    
#     @staticmethod
#     def can_send_email(email_type: str, candidate_status: str) -> bool:
#         """
#         Check if email can be sent based on candidate status.
        
#         Workflow validation logic:
#         - Each email type has a list of allowed candidate statuses
#         - Email can only be sent if candidate is in one of those statuses
        
#         Args:
#             email_type: Type of email to send
#             candidate_status: Current status of candidate
        
#         Returns:
#             True if email can be sent, False otherwise
#         """
        
#         if not EmailValidator.is_valid_email_type(email_type):
#             return False
        
#         if not EmailValidator.is_valid_candidate_status(candidate_status):
#             return False
        
#         allowed_statuses = EMAIL_TYPES[email_type]["allowed_statuses"]
#         return candidate_status in allowed_statuses
    
#     @staticmethod
#     def get_validation_error(email_type: str, candidate_status: str) -> str:
#         """
#         Get a user-friendly error message for validation failure.
        
#         Args:
#             email_type: Type of email to send
#             candidate_status: Current status of candidate
        
#         Returns:
#             Error message string
#         """
        
#         if not EmailValidator.is_valid_email_type(email_type):
#             return f"Invalid email type: {email_type}. Available types: {', '.join(EMAIL_TYPES.keys())}"
        
#         if not EmailValidator.is_valid_candidate_status(candidate_status):
#             return f"Invalid candidate status: {candidate_status}. Valid statuses: {', '.join(VALID_CANDIDATE_STATUSES)}"
        
#         allowed_statuses = EMAIL_TYPES[email_type]["allowed_statuses"]
#         return (
#             f"Cannot send '{EMAIL_TYPES[email_type]['name']}' to candidate with status '{candidate_status}'. "
#             f"Allowed statuses: {', '.join(allowed_statuses)}"
#         )
    
#     @staticmethod
#     def validate_extra_data(email_type: str, extra_data: dict) -> tuple[bool, str]:
#         """
#         Validate that required extra data is provided for email type.
        
#         Args:
#             email_type: Type of email to send
#             extra_data: Extra data provided by user
        
#         Returns:
#             Tuple of (is_valid, error_message)
#         """
        
#         if not EmailValidator.is_valid_email_type(email_type):
#             return False, f"Invalid email type: {email_type}"
        
#         email_def = EMAIL_TYPES[email_type]
#         required_fields = email_def.get("requires_extra_data", [])
        
#         if not required_fields:
#             return True, ""
        
#         if not extra_data:
#             missing_fields = ", ".join(required_fields)
#             return False, f"Missing required data for {email_type}: {missing_fields}"
        
#         missing_fields = [field for field in required_fields if field not in extra_data]
        
#         if missing_fields:
#             return False, f"Missing required data: {', '.join(missing_fields)}"
        
#         return True, ""
    
#     @staticmethod
#     def get_email_type_info(email_type: str) -> dict:
#         """
#         Get detailed information about an email type.
        
#         Args:
#             email_type: Type of email
        
#         Returns:
#             Dictionary with email type information or empty dict if not found
#         """
#         return EMAIL_TYPES.get(email_type, {})
    
#     @staticmethod
#     def list_email_types() -> list[dict]:
#         """
#         Get list of all available email types with descriptions.
        
#         Returns:
#             List of email type definitions
#         """
#         return [
#             {
#                 "key": key,
#                 "name": value["name"],
#                 "description": value["description"],
#                 "allowed_statuses": value["allowed_statuses"],
#             }
#             for key, value in EMAIL_TYPES.items()
#         ]
# app/services/email_validator.py
"""
Email validation service.
Validates email type against candidate status and other rules.
"""

from app.config import EMAIL_TYPES, VALID_CANDIDATE_STATUSES


class EmailValidator:
    """Validates email sending requests"""
    
    @staticmethod
    def is_valid_email_type(email_type: str) -> bool:
        """
        Check if email type is defined.
        
        Args:
            email_type: Email type to validate
        
        Returns:
            True if email type exists in EMAIL_TYPES
        """
        return email_type in EMAIL_TYPES
    
    @staticmethod
    def is_valid_candidate_status(candidate_status: str) -> bool:
        """
        Check if candidate status is valid.
        
        Args:
            candidate_status: Candidate status to validate
        
        Returns:
            True if status is in VALID_CANDIDATE_STATUSES
        """
        return candidate_status in VALID_CANDIDATE_STATUSES
    
    @staticmethod
    def can_send_email(email_type: str, candidate_status: str) -> bool:
        """
        Check if email can be sent based on candidate status.
        
        Workflow validation logic:
        - Each email type has a list of allowed candidate statuses
        - Email can only be sent if candidate is in one of those statuses
        
        Args:
            email_type: Type of email to send
            candidate_status: Current status of candidate
        
        Returns:
            True if email can be sent, False otherwise
        """
        
        if not EmailValidator.is_valid_email_type(email_type):
            return False
        
        if not EmailValidator.is_valid_candidate_status(candidate_status):
            return False
        
        allowed_statuses = EMAIL_TYPES[email_type]["allowed_statuses"]
        return candidate_status in allowed_statuses
    
    @staticmethod
    def get_validation_error(email_type: str, candidate_status: str) -> str:
        """
        Get a user-friendly error message for validation failure.
        
        Args:
            email_type: Type of email to send
            candidate_status: Current status of candidate
        
        Returns:
            Error message string
        """
        
        if not EmailValidator.is_valid_email_type(email_type):
            return f"Invalid email type: {email_type}. Available types: {', '.join(EMAIL_TYPES.keys())}"
        
        if not EmailValidator.is_valid_candidate_status(candidate_status):
            return f"Invalid candidate status: {candidate_status}. Valid statuses: {', '.join(VALID_CANDIDATE_STATUSES)}"
        
        allowed_statuses = EMAIL_TYPES[email_type]["allowed_statuses"]
        return (
            f"Cannot send '{EMAIL_TYPES[email_type]['name']}' to candidate with status '{candidate_status}'. "
            f"Allowed statuses: {', '.join(allowed_statuses)}"
        )
    
    @staticmethod
    def validate_extra_data(email_type: str, extra_data: dict) -> tuple[bool, str]:
        """
        Validate that required extra data is provided for email type.
        
        Args:
            email_type: Type of email to send
            extra_data: Extra data provided by user
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        
        if not EmailValidator.is_valid_email_type(email_type):
            return False, f"Invalid email type: {email_type}"
        
        email_def = EMAIL_TYPES[email_type]
        required_fields = email_def.get("requires_extra_data", [])
        
        if not required_fields:
            return True, ""
        
        if not extra_data:
            missing_fields = ", ".join(required_fields)
            return False, f"Missing required data for {email_type}: {missing_fields}"
        
        missing_fields = [
            field for field in required_fields
            if field not in extra_data or not str(extra_data.get(field, "")).strip()
        ]

        # Role-specific responsibilities are mandatory for selection emails.
        if email_type == "selection_email" and not str(extra_data.get("role_tasks", "")).strip():
            missing_fields.append("role_tasks")

        if missing_fields:
            return False, f"Missing required data: {', '.join(dict.fromkeys(missing_fields))}"

        return True, ""
    
    @staticmethod
    def get_email_type_info(email_type: str) -> dict:
        """
        Get detailed information about an email type.
        
        Args:
            email_type: Type of email
        
        Returns:
            Dictionary with email type information or empty dict if not found
        """
        return EMAIL_TYPES.get(email_type, {})
    
    @staticmethod
    def list_email_types() -> list[dict]:
        """
        Get list of all available email types with descriptions.
        
        Returns:
            List of email type definitions
        """
        return [
            {
                "key": key,
                "name": value["name"],
                "description": value["description"],
                "allowed_statuses": value["allowed_statuses"],
            }
            for key, value in EMAIL_TYPES.items()
        ]
