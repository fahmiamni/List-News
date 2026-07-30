"""Data models for news articles."""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class NewsArticle:
    """Represents a single news article."""
    id: str
    title: str
    summary: str
    full_summary: str
    url: str
    category: str
    state: str
    source: str
    published_date: str
    fetched_date: str
    generated_date: str
    is_local: bool
    image_url: str = ""
    country: str = ""
    ai_summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "NewsArticle":
        if "generated_date" not in data:
            data["generated_date"] = data.get("fetched_date", "")
        return cls(**data)