"""OpenRouter API client for news summarization."""
import requests
import json

from config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL


def summarize_article(text: str) -> str:
    """Summarize article text using DeepSeek V4 Flash via OpenRouter.

    Returns:
        Summary text with **bold** markdown for key points,
        or an error message if the API call fails.
    """
    if not text.strip():
        return "No article content available to summarize."

    if not OPENROUTER_API_KEY:
        return (
            "OpenRouter API key not configured. "
            "Set OPENROUTER_API_KEY in your .env file."
        )

    system_prompt = (
        "You are a news summarizer. Summarize the given article in "
        "approximately 200-300 words. Highlight key points by enclosing "
        "them in **double asterisks**. Use plain English. Be concise."
    )

    user_prompt = (
        f"Please summarize this news article:\n\n{text[:4000]}"
    )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/News-Curator-Kimi2-List",
    }

    try:
        resp = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()
        return summary
    except requests.RequestException as e:
        print(f"   [OPENROUTER] API call failed: {e}")
        return f"Failed to generate summary: {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"   [OPENROUTER] Response parse error: {e}")
        return f"Failed to parse summary response: {e}"
