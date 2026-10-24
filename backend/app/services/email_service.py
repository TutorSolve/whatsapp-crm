import os
import logging
import requests

# ============================================================================
# SENDGRID IMPLEMENTATION (COMMENTED OUT AS PER BREVO MIGRATION)
# ============================================================================
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
#
# def _sendgrid_send(to_email: str, subject: str, html_content: str) -> bool:
#     api_key = os.environ.get("SENDGRID_API_KEY", "dummy_dev_key")
#     from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@whatsappcrm.com")
#     if api_key == "dummy_dev_key":
#         return True
#     message = Mail(
#         from_email=from_email,
#         to_emails=to_email,
#         subject=subject,
#         html_content=html_content,
#     )
#     try:
#         sg = SendGridAPIClient(api_key)
#         sg.send(message)
#         return True
#     except Exception as e:
#         logger.error("SendGrid send failed: %s", e)
#         return False
# ============================================================================

logger = logging.getLogger(__name__)

class EmailService:
    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

    @classmethod
    def _send_email(cls, to_email: str, full_name: str, subject: str, html_content: str) -> bool:
        """
        Sends an email using Brevo (formerly Sendinblue) Transactional API.
        Falls back to logging link in dev mode when API key is unconfigured.
        """
        api_key = os.environ.get("BREVO_API_KEY") or os.environ.get("SENDGRID_API_KEY", "dummy_dev_key")
        from_email = os.environ.get("BREVO_FROM_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL", "tutorsolve0@gmail.com")
        from_name = os.environ.get("BREVO_FROM_NAME") or os.environ.get("SENDGRID_FROM_NAME", "TutorSolve CRM")

        if not api_key or api_key == "dummy_dev_key":
            logger.info("[DEV MODE] Skipping real email to %s (API key not configured).", to_email)
            return True

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "sender": {
                "name": from_name,
                "email": from_email,
            },
            "to": [
                {
                    "email": to_email,
                    "name": full_name or to_email,
                }
            ],
            "subject": subject,
            "htmlContent": html_content,
        }

        try:
            response = requests.post(cls.BREVO_API_URL, headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 201, 202):
                logger.info("Successfully sent email to %s via Brevo. Message ID: %s", to_email, response.json().get("messageId"))
                return True
            else:
                logger.error("Failed to send email to %s via Brevo. Status: %s, Response: %s", to_email, response.status_code, response.text)
                return False
        except Exception as e:
            logger.error("Failed to send email to %s via Brevo: %s", to_email, str(e))
            logger.exception(e)
            return False

    @classmethod
    def send_welcome_email(cls, to_email: str, full_name: str, setup_link: str) -> bool:
        """
        Sends an automated welcome email with a link to set the account's own
        password (same token-based flow as password reset).
        """
        api_key = os.environ.get("BREVO_API_KEY") or os.environ.get("SENDGRID_API_KEY", "dummy_dev_key")
        if not api_key or api_key == "dummy_dev_key":
            logger.info("[DEV MODE] Welcome Setup Link for %s: %s", to_email, setup_link)

        subject = "Welcome to WhatsApp CRM"
        html_content = f"""
            <strong>Hello {full_name},</strong><br><br>
            Your account for the WhatsApp CRM has been created by your Admin.<br>
            Click the link below to set your password and log in. This link expires in 30 minutes:<br><br>
            <a href="{setup_link}">{setup_link}</a><br><br>
            <em>Note: Please check your spam or junk folder if you don't see this in your inbox.</em><br><br>
            <em>If you weren't expecting this, contact your Admin.</em>
        """

        # --- PREVIOUS SENDGRID CALL (COMMENTED OUT) ---
        # message = Mail(
        #     from_email=from_email,
        #     to_emails=to_email,
        #     subject='Welcome to WhatsApp CRM',
        #     html_content=...
        # )
        # sg = SendGridAPIClient(api_key)
        # sg.send(message)
        # ----------------------------------------------

        return cls._send_email(to_email=to_email, full_name=full_name, subject=subject, html_content=html_content)

    @classmethod
    def send_password_reset_email(cls, to_email: str, full_name: str, reset_link: str) -> bool:
        """
        Sends a password reset link. Returns True if sent (or intentionally
        skipped in local dev), False if a real send attempt failed.
        """
        api_key = os.environ.get("BREVO_API_KEY") or os.environ.get("SENDGRID_API_KEY", "dummy_dev_key")
        if not api_key or api_key == "dummy_dev_key":
            logger.info("[DEV MODE] Password Reset Link for %s: %s", to_email, reset_link)

        subject = "Reset your WhatsApp CRM password"
        html_content = f"""
            <strong>Hello {full_name},</strong><br><br>
            We received a request to reset your WhatsApp CRM password.<br>
            Click the link below to choose a new password. This link expires in 30 minutes:<br><br>
            <a href="{reset_link}">{reset_link}</a><br><br>
            <em>Note: Please check your spam or junk folder if you don't see this in your inbox.</em><br><br>
            <em>If you didn't request this, you can safely ignore this email.</em>
        """

        # --- PREVIOUS SENDGRID CALL (COMMENTED OUT) ---
        # message = Mail(
        #     from_email=from_email,
        #     to_emails=to_email,
        #     subject='Reset your WhatsApp CRM password',
        #     html_content=...
        # )
        # sg = SendGridAPIClient(api_key)
        # sg.send(message)
        # ----------------------------------------------

        return cls._send_email(to_email=to_email, full_name=full_name, subject=subject, html_content=html_content)

