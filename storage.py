"""Local JSON storage for news data."""
import json
import os
from datetime import datetime
from typing import List, Dict
from models import NewsArticle, NewsEncoder
from config import DATA_FILE


class NewsStorage:
    """Handles reading and writing news data to local JSON file."""
    
    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
    
    def save_news(self, articles: List[NewsArticle]) -> None:
        """Save news articles to JSON file."""
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=NewsEncoder)
    
    def merge_news(self, new_articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Merge new articles with existing ones.
        - If article URL already exists, replace it with the new version (keep fetched_date for sorting)
        - If article is new, add it
        - Returns the merged list sorted by fetched_date (newest first)
        """
        # Load existing articles
        existing_data = self.load_news()
        existing_articles = [NewsArticle.from_dict(a) for a in existing_data.get("articles", [])]
        
        # Create a dict keyed by URL for quick lookup
        # Use URL as unique identifier since ID is derived from URL
        article_map = {article.url: article for article in existing_articles}
        
        # Merge new articles
        for new_article in new_articles:
            if new_article.url in article_map:
                # Article exists - replace it with new data, updating fetched_date
                # to the fresh publish timestamp parsed from Brave's age field
                existing_article = article_map[new_article.url]
                # Update with new data; fallback to existing image_url/country if new values are empty
                merged_article = NewsArticle(
                    id=new_article.id,
                    title=new_article.title,
                    summary=new_article.summary,
                    full_summary=new_article.full_summary,
                    url=new_article.url,
                    category=new_article.category,
                    state=new_article.state,
                    source=new_article.source,
                    published_date=new_article.published_date,
                    fetched_date=new_article.fetched_date,  # Use fresh publish timestamp from re-fetch
                    generated_date=existing_article.generated_date,  # Keep original generation date
                    is_local=new_article.is_local,
                    image_url=new_article.image_url or existing_article.image_url,
                    country=new_article.country or existing_article.country,
                    ai_summary=existing_article.ai_summary,  # Preserve cached summary
                )
                article_map[new_article.url] = merged_article
            else:
                # New article - add it
                article_map[new_article.url] = new_article
        
        # Convert back to list and sort by fetched_date (newest first)
        merged_list = list(article_map.values())
        merged_list.sort(key=lambda x: x.fetched_date, reverse=True)
        
        # Save merged list
        self.save_news(merged_list)
        
        return merged_list
    
    def load_news(self) -> Dict:
        """Load news articles from JSON file."""
        if not os.path.exists(self.filepath):
            return {
                "last_updated": None,
                "total_count": 0,
                "articles": []
            }
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading news data: {e}")
            return {
                "last_updated": None,
                "total_count": 0,
                "articles": []
            }
    
    def get_articles(self) -> List[NewsArticle]:
        """Get list of NewsArticle objects from storage."""
        data = self.load_news()
        return [NewsArticle.from_dict(article) for article in data.get("articles", [])]
    
    def update_article(self, article_id: str, field: str, value: str) -> bool:
        """Update a single field on an article identified by ID and save."""
        articles = self.get_articles()
        for article in articles:
            if article.id == article_id:
                setattr(article, field, value)
                self.save_news(articles)
                return True
        return False

    def clear_storage(self) -> None:
        """Clear all stored news data."""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
