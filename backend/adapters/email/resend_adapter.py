"""
Resend email service adapter.
"""

from typing import Optional
import resend

from infrastructure.config.settings import settings


class ResendEmailService:
    """Email service using Resend API."""

    def __init__(self):
        if settings.resend_api_key:
            resend.api_key = settings.resend_api_key
        self._from_email = settings.resend_from_email
        self._frontend_url = settings.frontend_url

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
    ) -> bool:
        """
        Send email verification email.

        Args:
            to_email: Recipient email address
            user_name: User's name for personalization
            verification_token: JWT verification token

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.resend_api_key:
            print(f"[DEV] Verification email for {to_email}: {self._frontend_url}/verify-email?token={verification_token}")
            return True

        verification_url = f"{self._frontend_url}/verify-email?token={verification_token}"

        try:
            resend.Emails.send({
                "from": self._from_email,
                "to": to_email,
                "subject": "Verify your A-Stats Content account",
                "html": self._get_verification_email_html(user_name, verification_url),
            })
            return True
        except Exception as e:
            print(f"Failed to send verification email: {e}")
            return False

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            user_name: User's name for personalization
            reset_token: JWT password reset token

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.resend_api_key:
            print(f"[DEV] Password reset email for {to_email}: {self._frontend_url}/reset-password?token={reset_token}")
            return True

        reset_url = f"{self._frontend_url}/reset-password?token={reset_token}"

        try:
            resend.Emails.send({
                "from": self._from_email,
                "to": to_email,
                "subject": "Reset your A-Stats Content password",
                "html": self._get_password_reset_email_html(user_name, reset_url),
            })
            return True
        except Exception as e:
            print(f"Failed to send password reset email: {e}")
            return False

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
    ) -> bool:
        """
        Send welcome email after verification.

        Args:
            to_email: Recipient email address
            user_name: User's name for personalization

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.resend_api_key:
            print(f"[DEV] Welcome email for {to_email}")
            return True

        try:
            resend.Emails.send({
                "from": self._from_email,
                "to": to_email,
                "subject": "Welcome to A-Stats Content!",
                "html": self._get_welcome_email_html(user_name),
            })
            return True
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
            return False

    async def send_project_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        project_name: str,
        role: str,
        invitation_url: str,
    ) -> bool:
        """
        Send project invitation email.

        Args:
            to_email: Recipient email address
            inviter_name: Name of the person who sent the invitation
            project_name: Name of the project
            role: Role the user will have in the project
            invitation_url: URL to accept the invitation

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.resend_api_key:
            print(f"[DEV] Project invitation email for {to_email}: {invitation_url}")
            return True

        try:
            resend.Emails.send({
                "from": self._from_email,
                "to": to_email,
                "subject": f"You've been invited to join {project_name} on A-Stats",
                "html": self._get_project_invitation_email_html(
                    inviter_name, project_name, role, invitation_url
                ),
            })
            return True
        except Exception as e:
            print(f"Failed to send project invitation email: {e}")
            return False

    def _get_verification_email_html(self, user_name: str, verification_url: str) -> str:
        """Generate verification email HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #FFF8F0; padding: 40px 20px;">
            <div style="max-width: 560px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ed8f73, #da7756); border-radius: 12px; margin: 0 auto;"></div>
                    <h1 style="color: #1A1A2E; font-size: 24px; margin: 16px 0 0;">A-Stats Content</h1>
                </div>

                <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Verify your email address</h2>

                <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
                    Hi {user_name},<br><br>
                    Thanks for signing up for A-Stats Content! Please verify your email address by clicking the button below.
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{verification_url}" style="display: inline-block; background: #da7756; color: white; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 500;">
                        Verify Email Address
                    </a>
                </div>

                <p style="color: #8B8BA7; font-size: 14px; line-height: 1.6;">
                    If you didn't create an account, you can safely ignore this email.
                </p>

                <hr style="border: none; border-top: 1px solid #F1F3F5; margin: 32px 0;">

                <p style="color: #8B8BA7; font-size: 12px; text-align: center;">
                    This link will expire in 24 hours.
                </p>
            </div>
        </body>
        </html>
        """

    def _get_password_reset_email_html(self, user_name: str, reset_url: str) -> str:
        """Generate password reset email HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #FFF8F0; padding: 40px 20px;">
            <div style="max-width: 560px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ed8f73, #da7756); border-radius: 12px; margin: 0 auto;"></div>
                    <h1 style="color: #1A1A2E; font-size: 24px; margin: 16px 0 0;">A-Stats Content</h1>
                </div>

                <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Reset your password</h2>

                <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
                    Hi {user_name},<br><br>
                    We received a request to reset your password. Click the button below to choose a new password.
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{reset_url}" style="display: inline-block; background: #da7756; color: white; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 500;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #8B8BA7; font-size: 14px; line-height: 1.6;">
                    If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
                </p>

                <hr style="border: none; border-top: 1px solid #F1F3F5; margin: 32px 0;">

                <p style="color: #8B8BA7; font-size: 12px; text-align: center;">
                    This link will expire in 1 hour.
                </p>
            </div>
        </body>
        </html>
        """

    def _get_welcome_email_html(self, user_name: str) -> str:
        """Generate welcome email HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #FFF8F0; padding: 40px 20px;">
            <div style="max-width: 560px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ed8f73, #da7756); border-radius: 12px; margin: 0 auto;"></div>
                    <h1 style="color: #1A1A2E; font-size: 24px; margin: 16px 0 0;">A-Stats Content</h1>
                </div>

                <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">Welcome to A-Stats Content!</h2>

                <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
                    Hi {user_name},<br><br>
                    Your email has been verified and your account is now active. You're ready to start creating amazing therapeutic content with AI!
                </p>

                <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #1A1A2E; font-size: 16px; margin: 0 0 16px;">Get started:</h3>
                    <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                        <li>Create your first article outline</li>
                        <li>Generate SEO-optimized content</li>
                        <li>Design custom AI images</li>
                        <li>Connect your WordPress site</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{self._frontend_url}/dashboard" style="display: inline-block; background: #da7756; color: white; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 500;">
                        Go to Dashboard
                    </a>
                </div>

                <hr style="border: none; border-top: 1px solid #F1F3F5; margin: 32px 0;">

                <p style="color: #8B8BA7; font-size: 12px; text-align: center;">
                    Need help? Reply to this email or visit our help center.
                </p>
            </div>
        </body>
        </html>
        """

    def _get_project_invitation_email_html(
        self, inviter_name: str, project_name: str, role: str, invitation_url: str
    ) -> str:
        """Generate project invitation email HTML."""
        # Format role nicely
        role_display = role.title()

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #FFF8F0; padding: 40px 20px;">
            <div style="max-width: 560px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #ed8f73, #da7756); border-radius: 12px; margin: 0 auto;"></div>
                    <h1 style="color: #1A1A2E; font-size: 24px; margin: 16px 0 0;">A-Stats Content</h1>
                </div>

                <h2 style="color: #1A1A2E; font-size: 20px; margin-bottom: 16px;">You've been invited to join a project!</h2>

                <p style="color: #4A4A68; line-height: 1.6; margin-bottom: 24px;">
                    {inviter_name} has invited you to join <strong>{project_name}</strong> on A-Stats Content.
                </p>

                <div style="background: #F8F9FA; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #1A1A2E; font-size: 16px; margin: 0 0 16px;">Invitation Details:</h3>
                    <ul style="color: #4A4A68; margin: 0; padding-left: 20px; line-height: 1.8;">
                        <li><strong>Project:</strong> {project_name}</li>
                        <li><strong>Your role:</strong> {role_display}</li>
                        <li><strong>Invited by:</strong> {inviter_name}</li>
                    </ul>
                </div>

                <div style="background: #FFF8F0; border-left: 4px solid #da7756; padding: 16px; margin-bottom: 24px;">
                    <p style="color: #4A4A68; margin: 0; font-size: 14px; line-height: 1.6;">
                        <strong>What is A-Stats?</strong><br>
                        A-Stats Content is an AI-powered platform for creating SEO-optimized therapeutic content.
                        Generate articles, outlines, and images with advanced AI tools.
                    </p>
                </div>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{invitation_url}" style="display: inline-block; background: #da7756; color: white; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 500;">
                        Accept Invitation
                    </a>
                </div>

                <p style="color: #8B8BA7; font-size: 14px; line-height: 1.6; text-align: center;">
                    If you don't have an A-Stats account yet, you'll be prompted to create one.
                </p>

                <hr style="border: none; border-top: 1px solid #F1F3F5; margin: 32px 0;">

                <p style="color: #8B8BA7; font-size: 12px; text-align: center;">
                    This invitation will expire in 7 days.<br>
                    If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """


# Singleton instance
email_service = ResendEmailService()
