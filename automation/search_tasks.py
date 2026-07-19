import os
import socket
import urllib.parse
import urllib.request
import json
import platform
import re
import ssl
from pathlib import Path
from datetime import datetime
from html import unescape
from html.parser import HTMLParser


class _SimpleHTMLTextExtractor(HTMLParser):
    """Tiny HTML to text extractor (stdlib only)."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._chunks = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        tag = (tag or "").lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        tag = (tag or "").lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        text = (data or "").strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text
        self._chunks.append(text)

    def text(self):
        merged = " ".join(self._chunks)
        merged = re.sub(r"\s+", " ", unescape(merged)).strip()
        return merged


def _build_result(action, path, status, message, item_type="Search", extra=None):
    return {
        "action": action,
        "name": Path(path).name if path else "",
        "path": str(Path(path).expanduser().resolve()) if path else "",
        "type": item_type,
        "status": status,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "details": extra,
    }


def _has_internet(timeout=2):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout)
        return True
    except OSError:
        return False


def _try_fetch_json(url, timeout=8):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None


def fetch_url_text(url, timeout=10, max_chars=5000):
    """Fetch and extract readable text from a URL."""
    def _read_once(target_url, insecure=False):
        req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
        context = ssl._create_unverified_context() if insecure else None
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            raw = resp.read()
            if "html" in content_type or b"<html" in raw[:500].lower():
                html = raw.decode("utf-8", errors="ignore")
                parser = _SimpleHTMLTextExtractor()
                parser.feed(html)
                body = parser.text()[:max_chars]
                return {
                    "status": "success",
                    "url": url,
                    "title": parser.title or target_url,
                    "text": body,
                    "source": target_url,
                }
            text = raw.decode("utf-8", errors="ignore")[:max_chars]
            return {
                "status": "success",
                "url": url,
                "title": target_url,
                "text": re.sub(r"\s+", " ", text).strip(),
                "source": target_url,
            }

    last_error = None

    # 1) direct fetch
    try:
        return _read_once(url, insecure=False)
    except Exception as e:
        last_error = e

    # 2) SSL-relaxed fallback (helps local Python SSL cert issues)
    try:
        return _read_once(url, insecure=True)
    except Exception as e:
        last_error = e

    # 3) mirror fallback for hard-to-parse pages
    try:
        mirror = f"https://r.jina.ai/http://{url.replace('https://', '').replace('http://', '')}"
        return _read_once(mirror, insecure=False)
    except Exception as e:
        last_error = e

    return {
        "status": "failed",
        "url": url,
        "title": url,
        "text": "",
        "message": str(last_error) if last_error else "Unknown fetch error",
    }


def collect_reference_material(urls, max_urls=5, max_chars_per_url=2500):
    """Collect summarized text from reference URLs for document generation."""
    clean_urls = []
    for u in urls or []:
        if not u:
            continue
        cu = u.strip().rstrip(').,;!')
        if cu.startswith("http://") or cu.startswith("https://"):
            clean_urls.append(cu)
    clean_urls = clean_urls[:max_urls]

    results = [fetch_url_text(u, max_chars=max_chars_per_url) for u in clean_urls]
    ok = [r for r in results if r.get("status") == "success" and r.get("text")]

    if not ok:
        fallback_lines = ["Provided source URLs (content fetch failed):"]
        for i, r in enumerate(results, 1):
            fallback_lines.append(f"{i}. {r.get('url', '')}")
        return {
            "status": "failed",
            "message": "No reference content could be fetched from the provided URLs.",
            "references": results,
            "combined_text": "\n".join(fallback_lines),
        }

    sections = []
    for i, r in enumerate(ok, 1):
        sections.append(f"Source {i}: {r.get('title', r.get('url'))}")
        sections.append(f"URL: {r.get('url')}")
        sections.append(r.get("text", ""))
        sections.append("")

    return {
        "status": "success",
        "message": f"Fetched {len(ok)} reference source(s).",
        "references": results,
        "combined_text": "\n".join(sections).strip(),
    }


def search_file(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []
    try:
        if not root_path.exists():
            return _build_result("Search File", root_path, "failed", "Search root does not exist", "File", extra=[])
        for item in root_path.rglob("*"):
            if item.is_file() and query.lower() in item.name.lower():
                matches.append(str(item.resolve()))
                if len(matches) >= max_results:
                    break
        return _build_result("Search File", root_path, "success", f"Found {len(matches)} file(s) matching '{query}'", "File", extra=matches)
    except Exception as e:
        return _build_result("Search File", root_path, "failed", str(e), "File", extra=[])


def search_folder(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []
    try:
        if not root_path.exists():
            return _build_result("Search Folder", root_path, "failed", "Search root does not exist", "Folder", extra=[])
        for item in root_path.rglob("*"):
            if item.is_dir() and query.lower() in item.name.lower():
                matches.append(str(item.resolve()))
                if len(matches) >= max_results:
                    break
        return _build_result("Search Folder", root_path, "success", f"Found {len(matches)} folder(s) matching '{query}'", "Folder", extra=matches)
    except Exception as e:
        return _build_result("Search Folder", root_path, "failed", str(e), "Folder", extra=[])


def search_applications(query=None, max_results=50):
    """Search for installed applications (cross-platform)."""
    current_os = platform.system()
    matches = []
    
    try:
        if current_os == "Darwin":
            # macOS: search /Applications and ~/Applications
            search_paths = [Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"]
            for search_path in search_paths:
                if not search_path.exists():
                    continue
                for item in search_path.rglob("*.app"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        
        elif current_os == "Windows":
            # Windows: search Program Files
            search_paths = [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            ]
            for root in search_paths:
                if not root.exists():
                    continue
                for item in root.rglob("*.exe"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        else:
            # Linux: search /usr/share/applications and /usr/bin
            desktop_paths = [Path("/usr/share/applications"), Path("/usr/local/share/applications"),
                             Path.home() / ".local/share/applications"]
            for root in desktop_paths:
                if not root.exists():
                    continue
                for item in root.glob("*.desktop"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
            
            # Also search /usr/bin for command-line apps
            bin_paths = [Path("/usr/bin"), Path("/usr/local/bin")]
            for bin_path in bin_paths:
                if not bin_path.exists():
                    continue
                for item in bin_path.iterdir():
                    if item.is_file() and os.access(str(item), os.X_OK):
                        if query is None or query.lower() in item.name.lower():
                            matches.append(str(item.resolve()))
                            if len(matches) >= max_results:
                                break
                if len(matches) >= max_results:
                    break
        
        return _build_result("Search Applications", query or "all", "success",
                            f"Found {len(matches)} installed application(s)", "Application", extra=matches)
    except Exception as e:
        return _build_result("Search Applications", query or "all", "failed", str(e), "Application", extra=[])


def research_topic(topic):
    if not topic:
        return ""
    if not _has_internet():
        return ""
    query = urllib.parse.quote(topic)
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&skip_disambig=1"
    data = _try_fetch_json(url)
    if not data:
        return ""
    abstract = data.get("AbstractText") or ""
    if abstract:
        return abstract
    related = data.get("RelatedTopics") or []
    if isinstance(related, list) and related:
        first = related[0]
        if isinstance(first, dict):
            return first.get("Text", "")
    return ""
