import os
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.config import settings
from src.core.middlewares.logging import logger

# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent / "email_templates"

# Initialize Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_EMAIL", "false").lower() == "true"

        if not self.use_mock:
            try:
                self.client = httpx.AsyncClient(
                    base_url="https://api.zeptomail.eu/v1.1",
                    headers={
                        "Authorization": f"Zoho-enczapikey {settings.ZEPTOMAIL_API_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to initialize email client: {e}")
                self.use_mock = True

        logger.info(f"Email service initialized (mock={self.use_mock})")

    def _render_template(self, template_name: str, **context) -> str:
        """Render email template with given context."""
        try:
            # Load the specific template content
            content_template = jinja_env.get_template(f"{template_name}.html")
            content_html = content_template.render(**context)

            # Wrap in base template
            base_template = jinja_env.get_template("base.html")
            full_html = base_template.render(
                content=content_html,
                app_name=context.get("app_name", settings.PROJECT_NAME),
                subject=context.get("subject", "Email Notification"),
            )

            return full_html
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return f"<html><body><p>{context.get('message', 'Email content')}</p></body></html>"

    async def _send_html_email(self, to_email: str, to_name: str, subject: str, html_content: str):
        """Send HTML email via ZeptoMail or mock it."""

        if self.use_mock:
            logger.info(f"[MOCK EMAIL] To: {to_email} ({to_name})")
            logger.info(f"[MOCK EMAIL] Subject: {subject}")
            logger.info(f"[MOCK EMAIL] Content length: {len(html_content)} characters")
            logger.info(f"[MOCK EMAIL] Preview: {html_content[:200]}...")
            return

        payload = {
            "from": {
                "address": settings.ZEPTOMAIL_FROM_EMAIL,
                "name": settings.ZEPTOMAIL_FROM_NAME,
            },
            "to": [{"email_address": {"address": to_email, "name": to_name}}],
            "subject": subject,
            "htmlbody": html_content,
        }

        try:
            response = await self.client.post("/email", json=payload)
            response.raise_for_status()
            logger.info(f"Email sent to {to_email}: {subject}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Email failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Email error: {e}")

    async def send_verification_code(self, email: str, code: str, name: str = "User"):
        """Send email verification code."""
        html_content = self._render_template(
            "verification_code",
            name=name,
            code=code,
            app_name=settings.PROJECT_NAME,
            subject="Verify Your Email Address",
        )

        await self._send_html_email(
            to_email=email,
            to_name=name,
            subject=f"Verify Your Email - {settings.PROJECT_NAME}",
            html_content=html_content,
        )

    async def send_welcome_email(self, email: str, name: str = "User"):
        """Send welcome email after successful registration."""
        html_content = self._render_template(
            "welcome",
            name=name,
            app_name=settings.PROJECT_NAME,
            subject=f"Welcome to {settings.PROJECT_NAME}",
        )

        await self._send_html_email(
            to_email=email,
            to_name=name,
            subject=f"Welcome to {settings.PROJECT_NAME}! 🎉",
            html_content=html_content,
        )

    async def send_reset_password_code(self, email: str, code: str, name: str = "User"):
        """Send password reset code."""
        html_content = self._render_template(
            "reset_password",
            name=name,
            code=code,
            app_name=settings.PROJECT_NAME,
            subject="Reset Your Password",
        )

        await self._send_html_email(
            to_email=email,
            to_name=name,
            subject=f"Password Reset Request - {settings.PROJECT_NAME}",
            html_content=html_content,
        )


email_service = EmailService()
