"""Flask web application for News Curator."""
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from collections import OrderedDict
from typing import List
import os
import sys

from fetcher import NewsFetcher
from storage import NewsStorage
from models import NewsArticle
import scraper

app = Flask(__name__)

# Initialize components
storage = NewsStorage()
fetcher = NewsFetcher()

# Category colors mapping
CATEGORY_COLORS = {
    "Politics": ("#E74C3C", "white"),
    "Crime": ("#2C3E50", "white"),
    "Economy": ("#27AE60", "white"),
    "Sports": ("#F39C12", "white"),
    "Technology": ("#3498DB", "white"),
    "Entertainment": ("#9B59B6", "white"),
    "Health": ("#E91E63", "white"),
    "Education": ("#00BCD4", "white"),
    "Environment": ("#4CAF50", "white"),
    "International": ("#607D8B", "white"),
    "Other": ("#95A5A6", "white"),
}


def get_category_color(category: str) -> tuple:
    """Get background and text color for a category."""
    return CATEGORY_COLORS.get(category, ("#95A5A6", "white"))


def get_all_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Return all articles without time filtering."""
    return articles


def get_relative_time(iso_date_str: str) -> str:
    """Convert an ISO datetime string to a relative time string like '3 hours ago'."""
    try:
        dt = datetime.fromisoformat(iso_date_str)
        now = datetime.now()
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds} seconds ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days < 30:
            return f"{days} day{'s' if days != 1 else ''} ago"
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    except Exception:
        return iso_date_str


def format_article_for_template(article: NewsArticle) -> dict:
    """Format article data for template rendering."""
    bg_color, text_color = get_category_color(article.category)
    # Show state for local news, country for global news
    location = article.state if article.is_local else (article.country or "Global")
    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "full_summary": article.full_summary,
        "url": article.url,
        "category": article.category,
        "category_bg": bg_color,
        "category_text": text_color,
        "state": article.state,
        "is_global": article.state == "Global",
        "source": article.source,
        "published_date": get_relative_time(article.fetched_date) if article.fetched_date else article.published_date,
        "fetched_date": article.fetched_date,
        "generated_date": article.generated_date,
        "is_local": article.is_local,
        "image_url": article.image_url,
        "location": location,
    }


def group_articles_by_category(articles: list) -> OrderedDict:
    """Group formatted articles by category, preserving defined order."""
    category_order = list(CATEGORY_COLORS.keys())
    groups = OrderedDict()
    for cat in category_order:
        groups[cat] = []

    extra = {}
    for article in articles:
        cat = article.get("category", "Other")
        if cat in groups:
            groups[cat].append(article)
        else:
            extra.setdefault(cat, []).append(article)

    result = OrderedDict((k, v) for k, v in groups.items() if v)
    result.update(extra)
    return result


@app.route("/")
def index():
    """Render the main page with news articles."""
    filter_type = request.args.get("filter", "all")
    articles = storage.get_articles()
    
    # Filter articles
    if filter_type == "local":
        filtered = [a for a in articles if a.is_local]
    elif filter_type == "global":
        filtered = [a for a in articles if not a.is_local]
    else:
        filtered = articles
    
    # Get all articles (no time filter)
    filtered = get_all_articles(filtered)
    
    # Sort by fetched_date (estimated publish time, newest first)
    filtered.sort(key=lambda x: x.fetched_date, reverse=True)
    
    # Format and group by category
    formatted = [format_article_for_template(a) for a in filtered]
    category_groups = group_articles_by_category(formatted)
    
    # Get stats
    total_count = len(get_all_articles(articles))
    local_count = sum(1 for a in get_all_articles(articles) if a.is_local)
    global_count = total_count - local_count
    
    return render_template(
        "index.html",
        category_groups=category_groups,
        filter_type=filter_type,
        total_count=total_count,
        local_count=local_count,
        global_count=global_count,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@app.route("/api/news")
def api_news():
    """API endpoint to get news articles as JSON."""
    filter_type = request.args.get("filter", "all")
    articles = storage.get_articles()
    
    # Filter articles
    if filter_type == "local":
        filtered = [a for a in articles if a.is_local]
    elif filter_type == "global":
        filtered = [a for a in articles if not a.is_local]
    else:
        filtered = articles
    
    # Get all articles (no time filter)
    filtered = get_all_articles(filtered)
    
    # Sort by fetched_date (estimated publish time, newest first)
    filtered.sort(key=lambda x: x.fetched_date, reverse=True)
    
    return jsonify([a.to_dict() for a in filtered])


@app.route("/api/update", methods=["POST"])
def api_update():
    """API endpoint to fetch and update news."""
    try:
        print("\n[Web] Update requested - fetching fresh news...")
        
        # Fetch new news
        new_articles = fetcher.fetch_all_news()
        
        print(f"   Fetched {len(new_articles)} articles")
        print(f"      - Local (Malaysia): {len([a for a in new_articles if a.is_local])}")
        print(f"      - Global: {len([a for a in new_articles if not a.is_local])}")
        
        # Merge with existing articles
        existing_articles = storage.get_articles()
        existing_urls = {a.url for a in existing_articles}
        new_count = sum(1 for a in new_articles if a.url not in existing_urls)
        updated_count = len(new_articles) - new_count
        
        merged_articles = storage.merge_news(new_articles)
        
        print(f"   Added {new_count} new, updated {updated_count} existing")
        print(f"   Total articles in storage: {len(merged_articles)}")
        
        return jsonify({
            "success": True,
            "message": f"Updated: {new_count} new, {updated_count} updated",
            "total": len(merged_articles),
            "new_count": new_count,
            "updated_count": updated_count
        })
    except Exception as e:
        print(f"[ERROR] Update failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    """API endpoint to summarize a specific article on-demand."""
    data = request.get_json(silent=True)
    if not data or "article_id" not in data:
        return jsonify({"success": False, "error": "Missing article_id"}), 400

    article_id = data["article_id"]
    articles = storage.get_articles()
    article = next((a for a in articles if a.id == article_id), None)
    if not article:
        return jsonify({"success": False, "error": "Article not found"}), 404

    # Return cached summary if available
    if article.ai_summary:
        return jsonify({"success": True, "summary": article.ai_summary, "cached": True})

    # Scrape full article text
    print(f"   [SUMMARIZE] Scraping: {article.url}")
    article_text = scraper.fetch_article_text(article.url)

    # Fallback to title + existing summary if scrape yields nothing
    if not article_text.strip():
        article_text = f"{article.title}. {article.summary} {article.full_summary}"

    # Generate summary via OpenRouter
    print(f"   [SUMMARIZE] Generating summary via OpenRouter...")
    from openrouter_client import summarize_article
    summary = summarize_article(article_text)
    if summary.startswith("Failed") or summary.startswith("OpenRouter"):
        return jsonify({"success": False, "error": summary}), 500

    # Cache the summary
    storage.update_article(article.id, "ai_summary", summary)
    print(f"   [SUMMARIZE] Done — cached for article {article.id}")

    return jsonify({"success": True, "summary": summary, "cached": False})


@app.route("/htmx/news-list")
def htmx_news_list():
    """HTMX endpoint to render news list (for dynamic updates)."""
    filter_type = request.args.get("filter", "all")
    articles = storage.get_articles()
    
    # Filter articles
    if filter_type == "local":
        filtered = [a for a in articles if a.is_local]
    elif filter_type == "global":
        filtered = [a for a in articles if not a.is_local]
    else:
        filtered = articles
    
    # Get all articles (no time filter)
    filtered = get_all_articles(filtered)
    
    # Sort by fetched_date (estimated publish time, newest first)
    filtered.sort(key=lambda x: x.fetched_date, reverse=True)
    
    # Format and group by category
    formatted = [format_article_for_template(a) for a in filtered]
    category_groups = group_articles_by_category(formatted)
    
    return render_template(
        "partials/news_list.html",
        category_groups=category_groups,
        filter_type=filter_type
    )


@app.route("/htmx/stats")
def htmx_stats():
    """HTMX endpoint to render stats (for dynamic updates)."""
    articles = get_all_articles(storage.get_articles())
    total_count = len(articles)
    local_count = sum(1 for a in articles if a.is_local)
    global_count = total_count - local_count
    
    return render_template(
        "partials/stats.html",
        total_count=total_count,
        local_count=local_count,
        global_count=global_count,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


def run_web_app(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """Run the Flask web application."""
    print("=" * 50)
    print("News Curator Web App")
    print("=" * 50)
    print(f"\nStarting web server...")
    print(f"   URL: http://{host}:{port}")
    print(f"   Press Ctrl+C to stop")
    print("=" * 50)
    
    # Ensure templates directory exists
    os.makedirs("templates/partials", exist_ok=True)
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_web_app(debug=True)
