"""Email service for notifications."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
import os
from rich.console import Console

console = Console()

class EmailService:
    """Service to send email notifications."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.mail.me.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.recipient = os.getenv("EMAIL_RECIPIENT")

    def send_notification(self, subject: str, body: str, recipient: Optional[str] = None) -> bool:
        """Send an email notification.

        Args:
            subject: Email subject.
            body: Email body (HTML supported).
            recipient: Recipient email (defaults to env var).

        Returns:
            True if successful, False otherwise.
        """
        if not self.username or not self.password:
            console.print("[yellow]Email credentials not configured. Skipping notification.[/yellow]")
            return False

        recipient = recipient or self.recipient
        if not recipient:
            console.print("[yellow]No recipient email configured.[/yellow]")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            console.print(f"[green]Email sent successfully to {recipient}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to send email: {e}[/red]")
            return False


