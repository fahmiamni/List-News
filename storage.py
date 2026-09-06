"""Local JSON storage for news data with in-memory cache."""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from models import NewsArticle
from config import DATA_FILE


class NewsStorage:
    """Handles reading and writing news data to local JSON file with in-memory cache."""

    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self._cached_articles: Optional[List[NewsArticle]] = None
        self._cache_time: Optional[datetime] = None

    def _invalidate_cache(self):
        self._cached_articles = None
        self._cache_time = None

    def save_news(self, articles: List[NewsArticle]) -> None:
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        self._invalidate_cache()

    def merge_news(self, new_articles: List[NewsArticle]) -> List[NewsArticle]:
        existing_data = self.load_news()
        existing_articles = [NewsArticle.from_dict(a) for a in existing_data.get("articles", [])]

        article_map = {article.url: article for article in existing_articles}

        for new_article in new_articles:
            if new_article.url in article_map:
                existing_article = article_map[new_article.url]
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
                    fetched_date=new_article.fetched_date,
                    generated_date=existing_article.generated_date,
                    is_local=new_article.is_local,
                    image_url=new_article.image_url or existing_article.image_url,
                    country=new_article.country or existing_article.country,
                    ai_summary=existing_article.ai_summary,
                )
                article_map[new_article.url] = merged_article
            else:
                article_map[new_article.url] = new_article

        merged_list = list(article_map.values())
        merged_list.sort(key=lambda x: x.fetched_date, reverse=True)

        self.save_news(merged_list)

        return merged_list

    def load_news(self) -> Dict:
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
        if self._cached_articles is not None:
            return self._cached_articles
        data = self.load_news()
        articles = [NewsArticle.from_dict(article) for article in data.get("articles", [])]
        self._cached_articles = articles
        self._cache_time = datetime.now()
        return articles

    def update_article(self, article_id: str, field: str, value: str) -> bool:
        articles = self.get_articles()
        for article in articles:
            if article.id == article_id:
                setattr(article, field, value)
                self.save_news(articles)
                return True
        return False

    def clear_storage(self) -> None:
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        self._invalidate_cache()