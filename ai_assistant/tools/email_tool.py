"""
AMAZON AI - Email Tool
Email integration for composing and managing emails.
"""
import sys
import logging
import webbrowser
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.tools.base_tool import BaseTool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class EmailTool(BaseTool):
    """
    Tool for email integration.
    
    Capabilities:
    - Open email clients
    - Compose emails with mailto links
    - Open webmail (Gmail, Outlook)
    - Create email templates
    """
    
    # Webmail URLs
    WEBMAIL_URLS = {
        "gmail": "https://mail.google.com/mail/?view=cm&fs=1&to={to}&su={subject}&body={body}",
        "outlook": "https://outlook.live.com/mail/0/deeplink/compose?to={to}&subject={subject}&body={body}",
        "yahoo": "https://compose.mail.yahoo.com/?to={to}&subject={subject}&body={body}",
    }
    
    @property
    def name(self) -> str:
        return "email"
    
    @property
    def description(self) -> str:
        return "Compose and send emails, open email clients"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Action: 'compose', 'open_webmail', 'open_client'",
                required=True
            ),
            ToolParameter(
                name="to",
                type="string",
                description="Recipient email address",
                required=False
            ),
            ToolParameter(
                name="subject",
                type="string",
                description="Email subject",
                required=False
            ),
            ToolParameter(
                name="body",
                type="string",
                description="Email body content",
                required=False
            ),
            ToolParameter(
                name="client",
                type="string",
                description="Email client: 'gmail', 'outlook', 'yahoo', 'default'",
                required=False,
                default="default"
            )
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute email action."""
        try:
            action = kwargs.get("action", "").lower()
            
            if action == "compose":
                return self._compose_email(
                    to=kwargs.get("to", ""),
                    subject=kwargs.get("subject", ""),
                    body=kwargs.get("body", ""),
                    client=kwargs.get("client", "default")
                )
            elif action == "open_webmail":
                return self._open_webmail(kwargs.get("client", "gmail"))
            elif action == "open_client":
                return self._open_email_client()
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    message=f"Unknown action: {action}. Use 'compose', 'open_webmail', or 'open_client'"
                )
        
        except Exception as e:
            logger.error(f"Email error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Email operation failed: {str(e)}"
            )
    
    def _compose_email(
        self,
        to: str = "",
        subject: str = "",
        body: str = "",
        client: str = "default"
    ) -> ToolResult:
        """Compose an email using mailto or webmail."""
        # Build mailto URL
        if client == "default" or client not in self.WEBMAIL_URLS:
            # Use system default email client
            mailto = f"mailto:{to}"
            params = []
            if subject:
                params.append(f"subject={quote(subject)}")
            if body:
                params.append(f"body={quote(body)}")
            if params:
                mailto += "?" + "&".join(params)
            
            webbrowser.open(mailto)
            
            return ToolResult(
                success=True,
                data={"to": to, "subject": subject, "client": "default"},
                message=f"📧 Opening email composer\n**To:** {to}\n**Subject:** {subject}"
            )
        
        else:
            # Use specific webmail
            url_template = self.WEBMAIL_URLS.get(client)
            if not url_template:
                return ToolResult(
                    success=False,
                    error=f"Unknown client: {client}",
                    message=f"Unknown email client: {client}"
                )
            
            url = url_template.format(
                to=quote(to) if to else "",
                subject=quote(subject) if subject else "",
                body=quote(body) if body else ""
            )
            
            webbrowser.open(url)
            
            return ToolResult(
                success=True,
                data={"to": to, "subject": subject, "client": client},
                message=f"📧 Opening {client.title()}\n**To:** {to}\n**Subject:** {subject}"
            )
    
    def _open_webmail(self, client: str = "gmail") -> ToolResult:
        """Open webmail in browser."""
        client_lower = client.lower()
        
        urls = {
            "gmail": "https://mail.google.com",
            "outlook": "https://outlook.live.com",
            "yahoo": "https://mail.yahoo.com",
            "protonmail": "https://mail.protonmail.com",
        }
        
        if client_lower in urls:
            webbrowser.open(urls[client_lower])
            return ToolResult(
                success=True,
                data={"client": client_lower},
                message=f"📧 Opening {client_lower.title()}"
            )
        else:
            return ToolResult(
                success=False,
                error=f"Unknown webmail: {client}",
                message=f"Unknown webmail service: {client}. Available: {', '.join(urls.keys())}"
            )
    
    def _open_email_client(self) -> ToolResult:
        """Open default email client."""
        # Use mailto: to open default client
        webbrowser.open("mailto:")
        return ToolResult(
            success=True,
            data={},
            message="📧 Opening default email client"
        )
    
    def create_template(self, template_type: str = "meeting") -> str:
        """Create an email template."""
        templates = {
            "meeting": """Subject: Meeting Request

Hi [Name],

I hope this email finds you well. I would like to schedule a meeting to discuss [topic].

Proposed time: [Date] at [Time]
Location: [Location/Video Call Link]

Please let me know if this works for you or suggest an alternative time.

Best regards,
[Your Name]""",
            
            "follow_up": """Subject: Follow Up: [Previous Topic]

Hi [Name],

I'm following up on [previous conversation/meeting/topic].

[Key points or action items]

Please let me know if you have any questions or need additional information.

Best regards,
[Your Name]""",
            
            "thank_you": """Subject: Thank You

Hi [Name],

I wanted to express my gratitude for [reason].

[Specific details about what you're thankful for]

Thank you again for [your time/help/support].

Best regards,
[Your Name]""",
            
            "introduction": """Subject: Introduction - [Your Name]

Hi [Name],

My name is [Your Name] and I'm [your role/position]. I'm reaching out because [reason].

[Brief background or context]

I would love to [connect/discuss/collaborate] regarding [topic].

Looking forward to hearing from you.

Best regards,
[Your Name]"""
        }
        
        return templates.get(template_type, templates["meeting"])
