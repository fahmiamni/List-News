"""Data models for news articles."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class NewsArticle:
    """Represents a single news article."""
    id: str
    title: str
    summary: str
    full_summary: str
    url: str
    category: str
    state: str  # "Global" for international news
    source: str
    published_date: str  # Original publication date from source
    fetched_date: str  # When this article was first fetched/generated
    generated_date: str  # When this article was generated in our system
    is_local: bool
    image_url: str = ""  # Thumbnail image URL from source
    country: str = ""  # Country for global news (detected from domain TLD)
    ai_summary: str = ""  # Cached on-demand summary from OpenRouter
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "NewsArticle":
        """Create from dictionary with backward compatibility."""
        # Handle old data that doesn't have generated_date
        if "generated_date" not in data:
            # Use fetched_date as fallback for old data
            data["generated_date"] = data.get("fetched_date", "")
        return cls(**data)


class NewsEncoder(json.JSONEncoder):
    """Custom JSON encoder for news data."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, NewsArticle):
            return obj.to_dict()
        return super().default(obj)
