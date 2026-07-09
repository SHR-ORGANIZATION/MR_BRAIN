"""
AMAZON AI - Web Browser Tool
Browser automation for web interactions.
"""
import sys
import logging
import webbrowser
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.tools.base_tool import BaseTool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class WebBrowserTool(BaseTool):
    """
    Tool for web browser automation.
    
    Capabilities:
    - Open websites
    - Search the web
    - Open URLs in default browser
    - Get page info (basic)
    """
    
    # Popular websites mapping
    POPULAR_SITES = {
        "google": "https://www.google.com",
        "youtube": "https://www.youtube.com",
        "github": "https://www.github.com",
        "stackoverflow": "https://stackoverflow.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "linkedin": "https://www.linkedin.com",
        "reddit": "https://www.reddit.com",
        "wikipedia": "https://www.wikipedia.org",
        "amazon": "https://www.amazon.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "gmail": "https://mail.google.com",
        "outlook": "https://outlook.live.com",
        "chatgpt": "https://chat.openai.com",
        "claude": "https://claude.ai",
        "whatsapp": "https://web.whatsapp.com",
        "telegram": "https://web.telegram.org",
    }
    
    @property
    def name(self) -> str:
        return "web_browser"
    
    @property
    def description(self) -> str:
        return "Open websites, search the web, and automate browser tasks"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Action: 'open_site', 'search', 'open_url'",
                required=True
            ),
            ToolParameter(
                name="site_name",
                type="string",
                description="Name of website (for open_site)",
                required=False
            ),
            ToolParameter(
                name="url",
                type="string",
                description="Full URL (for open_url)",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search query (for search)",
                required=False
            ),
            ToolParameter(
                name="search_engine",
                type="string",
                description="Search engine: 'google', 'bing', 'duckduckgo'",
                required=False,
                default="google"
            )
        ]
    
    @property
    def category(self) -> str:
        return "web"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute web browser action."""
        try:
            action = kwargs.get("action", "").lower()
            
            if action == "open_site":
                return self._open_site(kwargs.get("site_name", ""))
            elif action == "search":
                return self._search_web(
                    kwargs.get("query", ""),
                    kwargs.get("search_engine", "google")
                )
            elif action == "open_url":
                return self._open_url(kwargs.get("url", ""))
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    message=f"Unknown action: {action}. Use 'open_site', 'search', or 'open_url'"
                )
        
        except Exception as e:
            logger.error(f"Web browser error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Browser operation failed: {str(e)}"
            )
    
    def _open_site(self, site_name: str) -> ToolResult:
        """Open a popular website by name."""
        if not site_name:
            return ToolResult(
                success=False,
                error="Site name required",
                message="Please provide a website name"
            )
        
        site_lower = site_name.lower().strip()
        
        # Check popular sites
        if site_lower in self.POPULAR_SITES:
            url = self.POPULAR_SITES[site_lower]
            webbrowser.open(url)
            return ToolResult(
                success=True,
                data={"url": url, "site": site_name},
                message=f"🌐 Opening {site_name.title()}"
            )
        
        # Try to construct URL
        if "." in site_lower:
            url = f"https://{site_lower}"
        else:
            url = f"https://www.{site_lower}.com"
        
        webbrowser.open(url)
        return ToolResult(
            success=True,
            data={"url": url, "site": site_name},
            message=f"🌐 Opening {url}"
        )
    
    def _search_web(self, query: str, engine: str = "google") -> ToolResult:
        """Search the web using a search engine."""
        if not query:
            return ToolResult(
                success=False,
                error="Search query required",
                message="Please provide a search query"
            )
        
        # Search engine URLs
        engines = {
            "google": "https://www.google.com/search?q=",
            "bing": "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
        }
        
        engine_lower = engine.lower()
        if engine_lower not in engines:
            engine_lower = "google"
        
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = engines[engine_lower] + encoded_query
        
        webbrowser.open(url)
        return ToolResult(
            success=True,
            data={"query": query, "engine": engine_lower, "url": url},
            message=f"🔍 Searching {engine_lower.title()} for: '{query}'"
        )
    
    def _open_url(self, url: str) -> ToolResult:
        """Open a specific URL."""
        if not url:
            return ToolResult(
                success=False,
                error="URL required",
                message="Please provide a URL"
            )
        
        # Add https:// if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        webbrowser.open(url)
        return ToolResult(
            success=True,
            data={"url": url},
            message=f"🌐 Opening {url}"
        )
    
    def get_available_sites(self) -> List[str]:
        """Get list of available popular sites."""
        return list(self.POPULAR_SITES.keys())
