# app/services/template_renderer.py
"""
Template rendering service.
Renders Jinja2 email templates with candidate and context data.
"""

from pathlib import Path
from jinja2 import Template, TemplateNotFound, TemplateSyntaxError
from app.config import TEMPLATE_DIR, COMPANY_NAME


class TemplateRenderer:
    """Handles rendering of email templates"""
    
    @staticmethod
    def render(email_type: str, context: dict) -> tuple[str, str]:
        """
        Render an email template with context data.
        
        Args:
            email_type: Type of email (e.g., 'application_form')
            context: Dictionary with template variables
                - candidate_name: str (required)
                - candidate_email: str (required)
                - company_name: str (optional, defaults to config)
                - Other fields based on email type
        
        Returns:
            Tuple of (subject, html_body)
            
        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateSyntaxError: If template has syntax errors
            ValueError: If required context variables are missing
        """
        
        # Validate required context variables
        if "candidate_name" not in context:
            raise ValueError("candidate_name is required in context")
        if "candidate_email" not in context:
            raise ValueError("candidate_email is required in context")
        
        # Add company name if not provided
        if "company_name" not in context:
            context["company_name"] = COMPANY_NAME
        
        try:
            # Build template path
            template_path = TEMPLATE_DIR / f"{email_type}.html"
            
            if not template_path.exists():
                raise TemplateNotFound(f"Template not found: {email_type}.html")
            
            # Read template file
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            
            # Parse and render template
            template = Template(template_content)
            rendered_html = template.render(**context)
            
            # Extract subject from context (should be in email headers or passed separately)
            subject = context.get("subject", f"Message from {COMPANY_NAME}")
            
            return subject, rendered_html
            
        except TemplateNotFound as e:
            raise TemplateNotFound(f"Email template not found: {email_type}") from e
        except TemplateSyntaxError as e:
            raise TemplateSyntaxError(
                f"Syntax error in template {email_type}: {str(e)}", 
                e.lineno
            ) from e
        except Exception as e:
            raise Exception(f"Error rendering template {email_type}: {str(e)}") from e
    
    @staticmethod
    def render_subject(subject_template: str, context: dict) -> str:
        """
        Render email subject line with Jinja2 variables.
        
        Args:
            subject_template: Subject template string (e.g., "Interview at {{company_name}}")
            context: Dictionary with template variables
        
        Returns:
            Rendered subject string
        """
        try:
            template = Template(subject_template)
            return template.render(**context)
        except Exception as e:
            raise Exception(f"Error rendering subject: {str(e)}") from e
    
    @staticmethod
    def validate_template(email_type: str) -> bool:
        """
        Check if template exists and is valid.
        
        Args:
            email_type: Type of email
        
        Returns:
            True if template exists and is readable
        """
        try:
            template_path = TEMPLATE_DIR / f"{email_type}.html"
            return template_path.exists() and template_path.is_file()
        except Exception:
            return False
    
    @staticmethod
    def list_templates() -> list[str]:
        """
        List all available email templates.
        
        Returns:
            List of template filenames without .html extension
        """
        try:
            templates = []
            if TEMPLATE_DIR.exists():
                for template_file in TEMPLATE_DIR.glob("*.html"):
                    # Exclude base template
                    if template_file.name != "base.html":
                        templates.append(template_file.stem)
            return sorted(templates)
        except Exception:
            return []
