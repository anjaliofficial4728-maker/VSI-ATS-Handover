# app/services/email_service.py
"""
Email service for sending emails through Brevo.
Refactored for Phase 1 to support multiple email types and logging.
"""

import requests
from datetime import datetime
from typing import Optional
import base64      

from app.config import BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME
from app.database import supabase
from app.services.template_renderer import TemplateRenderer
from app.services.email_validator import EmailValidator
from app.models.email_log import EmailLogCreate, EmailLogUpdate

from app.config import (
    BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME,
    REGISTRATION_FORM_PDF_PATH,
)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    """Generic email service for sending emails and logging"""
    
    @staticmethod
    def send_email_to_brevo(
        to_email: str,
        subject: str,
        body: str,
        attachment_path: str = None,
    ) -> tuple[bool, str]:
        """
        Send email through Brevo API, optionally with a file attachment.
 
        Returns (success, message_id_or_error).
        """
        payload = {
            "sender": {
                "name": SENDER_NAME,
                "email": SENDER_EMAIL,
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": body,
        }
 
        # Attach a file if one was provided (used for the registration PDF).
        if attachment_path:
            try:
                with open(attachment_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                # Brevo wants a list of {name, content(base64)}.
                filename = attachment_path.replace("\\", "/").split("/")[-1]
                payload["attachment"] = [{"name": filename, "content": encoded}]
            except FileNotFoundError:
                return False, f"Attachment not found at {attachment_path}"
            except Exception as e:
                return False, f"Failed to read attachment: {str(e)}"
 
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        }
 
        try:
            response = requests.post(
                BREVO_API_URL,
                json=payload,
                headers=headers,
                timeout=15,   # slightly longer for attachment uploads
            )
 
            if response.status_code in (200, 201):
                try:
                    message_id = response.json().get("messageId", "unknown")
                except Exception:
                    message_id = "unknown"
                return True, message_id
            else:
                error_msg = f"Brevo API error: {response.status_code} - {response.text}"
                print(f"Email Error: {error_msg}")
                return False, error_msg
 
        except requests.exceptions.Timeout:
            print("Email Error: Brevo API timeout")
            return False, "Brevo API timeout"
        except requests.exceptions.RequestException as e:
            print(f"Email Error: {str(e)}")
            return False, f"Brevo API request error: {str(e)}"
        except Exception as e:
            print(f"Email Error: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def create_email_log(
        candidate_id: str,
        email_type: str,
        recipient_email: str,
        subject: str,
        status: str = "pending",
        brevo_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create an email log entry in the database.
        
        Args:
            candidate_id: ID of candidate
            email_type: Type of email
            recipient_email: Email recipient address
            subject: Email subject
            status: Email status ('pending', 'sent', 'failed')
            brevo_message_id: Message ID from Brevo
            error_message: Error message if failed
        
        Returns:
            Email log ID if successful, None if failed
        """
        
        try:
            response = supabase.table("email_logs").insert({
                "candidate_id": candidate_id,
                "email_type": email_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "status": status,
                "brevo_message_id": brevo_message_id,
                "error_message": error_message,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error creating email log: {str(e)}")
            return None
    
    @staticmethod
    def update_email_log(
        email_log_id: str,
        status: str,
        brevo_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update an email log entry.
        
        Args:
            email_log_id: ID of email log to update
            status: New status
            brevo_message_id: Message ID from Brevo
            error_message: Error message if failed
        
        Returns:
            True if successful, False otherwise
        """
        
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            if brevo_message_id:
                update_data["brevo_message_id"] = brevo_message_id
            
            if error_message:
                update_data["error_message"] = error_message
            
            if status == "sent":
                update_data["sent_at"] = datetime.utcnow().isoformat()
            
            response = supabase.table("email_logs").update(update_data).eq(
                "id", email_log_id
            ).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"Error updating email log: {str(e)}")
            return False
    
    @staticmethod
    def send_email(
        candidate_id: str,
        candidate_name: str,
        recipient_email: str,
        email_type: str,
        extra_data: Optional[dict] = None,
    ) -> tuple[bool, str, Optional[str]]:
        """
        Send email to candidate with full logging and validation.
        
        Args:
            candidate_id: ID of candidate
            candidate_name: Name of candidate
            recipient_email: Recipient email address
            email_type: Type of email to send
            extra_data: Additional data for template rendering
        
        Returns:
            Tuple of (success: bool, message: str, email_log_id: Optional[str])
        """
        
        email_log_id = None
        
        try:
            # Validate email type exists
            if not EmailValidator.is_valid_email_type(email_type):
                error_msg = f"Invalid email type: {email_type}"
                return False, error_msg, None
            
            # Validate extra data
            is_valid, error_msg = EmailValidator.validate_extra_data(
                email_type,
                extra_data or {}
            )
            if not is_valid:
                return False, error_msg, None
            
            # Build context for template rendering
            context = {
                "candidate_name": candidate_name,
                "candidate_email": recipient_email,
            }
            
            if extra_data:
                context.update(extra_data)
            
            # Render template
            try:
                subject, html_body = TemplateRenderer.render(email_type, context)
            except Exception as e:
                error_msg = f"Template rendering failed: {str(e)}"
                return False, error_msg, None
            
            # Create email log entry (pending status)
            email_log_id = EmailService.create_email_log(
                candidate_id=candidate_id,
                email_type=email_type,
                recipient_email=recipient_email,
                subject=subject,
                status="pending",
            )
            
            if not email_log_id:
                return False, "Failed to create email log", None
            
            # Attach the registration PDF for registration emails.
            attachment_path = None
            if email_type == "registration_form":
                attachment_path = REGISTRATION_FORM_PDF_PATH
 
            success, result = EmailService.send_email_to_brevo(
                to_email=recipient_email,
                subject=subject,
                body=html_body,
                attachment_path=attachment_path,
            )

            
            if success:
                # Update log with success
                EmailService.update_email_log(
                    email_log_id=email_log_id,
                    status="sent",
                    brevo_message_id=result,
                )
                return True, "Email sent successfully", email_log_id
            else:
                # Update log with failure
                EmailService.update_email_log(
                    email_log_id=email_log_id,
                    status="failed",
                    error_message=result,
                )
                return False, f"Failed to send email: {result}", email_log_id
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if email_log_id:
                EmailService.update_email_log(
                    email_log_id=email_log_id,
                    status="failed",
                    error_message=error_msg,
                )
            return False, error_msg, email_log_id
    
    # Legacy methods for backward compatibility
    
    @staticmethod
    def send_offer_email(name: str, to_email: str) -> bool:
        """
        Legacy method for sending offer email.
        Uses new generic send_email internally.
        """
        success, message, _ = EmailService.send_email(
            candidate_id="",  # Not available in legacy call
            candidate_name=name,
            recipient_email=to_email,
            email_type="selection_email",
        )
        return success
    
    @staticmethod
    def send_reminder_email(name: str, to_email: str) -> bool:
        """
        Legacy method for sending reminder email.
        Uses new generic send_email internally.
        """
        success, message, _ = EmailService.send_email(
            candidate_id="",  # Not available in legacy call
            candidate_name=name,
            recipient_email=to_email,
            email_type="reminder_email",
        )
        return success
