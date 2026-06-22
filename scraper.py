"""Article content scraper for news summarization."""
import requests
from urllib.parse import urlparse


def fetch_article_text(url: str) -> str:
    """Fetch and extract main article text from a URL.

    Tries multiple extraction strategies:
    1. <p> tags inside article/main/section
    2. All <p> tags
    3. <div> text blocks
    4. Meta description / og:description
    Returns the first strategy that yields enough text, or "" on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"   [SCRAPE] Fetch failed: {e}")
        return ""

    html = resp.text
    if len(html) < 200:
        print(f"   [SCRAPE] Response too short ({len(html)} bytes)")
        return ""

    try:
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return ""

    for tag in soup(["script", "style", "noscript", "nav", "footer",
                      "header", "aside", "form", "iframe"]):
        tag.decompose()

    # Strategy 1: <p> inside article/main/section
    for container in soup.find_all(["article", "main", "section"]):
        paragraphs = container.find_all("p")
        text = _extract_paragraphs(paragraphs)
        if text:
            return text

    # Strategy 2: all <p> tags in page
    all_paragraphs = soup.find_all("p")
    text = _extract_paragraphs(all_paragraphs)
    if text:
        return text

    # Strategy 3: long <div> text blocks
    divs = soup.find_all("div")
    div_texts = []
    for div in divs:
        t = div.get_text(" ", strip=True)
        if len(t) > 80:
            div_texts.append(t)
    if div_texts:
        combined = " ".join(div_texts)[:4000]
        if len(combined.split()) > 30:
            return _truncate(combined)

    # Strategy 4: meta description / og:description
    meta_desc = ""
    for attr in [
        {"property": "og:description"},
        {"name": "description"},
        {"property": "twitter:description"},
    ]:
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content"):
            meta_desc = tag["content"].strip()
            if len(meta_desc) > 50:
                break

    if meta_desc:
        # Also grab page title for context
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        combined = f"{title}. {meta_desc}" if title else meta_desc
        return _truncate(combined)

    # Strategy 5: extract all visible text from body
    body = soup.find("body")
    if body:
        full_text = body.get_text(" ", strip=True)
        # Take first 3000 chars — likely to contain main content
        if len(full_text) > 100:
            return _truncate(full_text[:3000])

    return ""


def _extract_paragraphs(paragraphs):
    """Extract text from paragraph tags, returning first 2000 words."""
    parts = []
    for p in paragraphs:
        t = p.get_text(" ", strip=True)
        if len(t) > 30:
            parts.append(t)
    if not parts:
        return ""
    combined = " ".join(parts)
    return _truncate(combined)


def _truncate(text: str) -> str:
    """Truncate text to 2000 words."""
    words = text.split()
    if len(words) > 2000:
        text = " ".join(words[:2000])
    return text
