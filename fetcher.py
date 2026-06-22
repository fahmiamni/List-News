"""News fetcher using Brave Search API with AI summarization."""
import requests
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse
from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, MAX_NEWS_PER_CATEGORY
from models import NewsArticle


def parse_brave_age(age_str: str, reference: datetime = None) -> str:
    """Parse Brave Search API 'age' field (e.g. '6h ago', '2d ago') into ISO datetime.

    Returns ISO-formatted datetime string. Falls back to reference time if unparseable.
    """
    if reference is None:
        reference = datetime.now()
    age_str = age_str.strip().lower()
    m = re.match(r"(\d+)\s*(h|hr|hrs|hour|hours|d|day|days|w|wk|wks|week|weeks|mo|mon|month|months|y|yr|yrs|year|years)\s+ago", age_str)
    if not m:
        return reference.isoformat()
    value = int(m.group(1))
    unit = m.group(2)
    if unit in ("h", "hr", "hrs", "hour", "hours"):
        delta = timedelta(hours=value)
    elif unit in ("d", "day", "days"):
        delta = timedelta(days=value)
    elif unit in ("w", "wk", "wks", "week", "weeks"):
        delta = timedelta(weeks=value)
    elif unit in ("mo", "mon", "month", "months"):
        delta = timedelta(days=value * 30)
    elif unit in ("y", "yr", "yrs", "year", "years"):
        delta = timedelta(days=value * 365)
    else:
        return reference.isoformat()
    return (reference - delta).isoformat()


class NewsFetcher:
    """Fetches news from Brave Search API and summarizes with AI."""
    
    def __init__(self):
        self.api_key = BRAVE_API_KEY
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        self._summarizer = None
    
    def _get_summarizer(self):
        """Lazy-load the AI summarizer."""
        if self._summarizer is None:
            from summarizer import NewsSummarizer
            self._summarizer = NewsSummarizer()
        return self._summarizer
    
    def _extract_source(self, url: str) -> str:
        """Extract domain name as source."""
        domain = urlparse(url).netloc
        return domain.replace("www.", "")

    def _detect_country_from_tld(self, url: str) -> str:
        """Detect country from source domain TLD."""
        domain = urlparse(url).netloc
        parts = domain.split(".")
        tld = parts[-1].lower() if len(parts) > 1 else ""

        # Handle two-part TLDs like .com.au, .co.uk
        # For subdomains, check the second-to-last part
        special_coms = {"co", "com", "org", "net", "gov", "edu", "ac"}
        if len(parts) >= 3 and parts[-2].lower() in special_coms:
            tld = parts[-2].lower() + "." + tld
        elif tld in special_coms and len(parts) >= 3:
            tld = parts[-1].lower() + "." + parts[-2].lower()

        tld_map = {
            "my": "Malaysia",
            "sg": "Singapore",
            "id": "Indonesia",
            "th": "Thailand",
            "ph": "Philippines",
            "vn": "Vietnam",
            "cn": "China",
            "hk": "Hong Kong",
            "tw": "Taiwan",
            "jp": "Japan",
            "kr": "South Korea",
            "in": "India",
            "pk": "Pakistan",
            "bd": "Bangladesh",
            "lk": "Sri Lanka",
            "au": "Australia",
            "nz": "New Zealand",
            "uk": "UK",
            "co.uk": "UK",
            "fr": "France",
            "de": "Germany",
            "it": "Italy",
            "es": "Spain",
            "pt": "Portugal",
            "nl": "Netherlands",
            "be": "Belgium",
            "ch": "Switzerland",
            "at": "Austria",
            "se": "Sweden",
            "no": "Norway",
            "dk": "Denmark",
            "fi": "Finland",
            "pl": "Poland",
            "cz": "Czech Republic",
            "ru": "Russia",
            "br": "Brazil",
            "mx": "Mexico",
            "ar": "Argentina",
            "cl": "Chile",
            "za": "South Africa",
            "ng": "Nigeria",
            "ke": "Kenya",
            "eg": "Egypt",
            "ae": "UAE",
            "sa": "Saudi Arabia",
            "il": "Israel",
            "tr": "Turkey",
            "ie": "Ireland",
            "ca": "Canada",
        }
        return tld_map.get(tld, "")
    
    def _classify_category(self, title: str, description: str) -> str:
        """Simple keyword-based category classification."""
        text = (title + " " + description).lower()
        
        keywords = {
            "Politics": ["politic", "government", "minister", "pm", "prime minister", "parliament", "election", "anwar", "coalition", "party", "vote"],
            "Crime": ["police", "arrest", "crime", "court", "trial", "murder", "theft", "fraud", "macc", "investigation", "charged", "jail", "prison"],
            "Economy": ["economy", "economic", "finance", "stock", "market", "trade", "investment", "gdp", "inflation", "ringgit", "bank", "rate"],
            "Sports": ["sport", "football", "soccer", "badminton", "olympic", "player", "team", "match", "tournament", "game", "win", "championship"],
            "Technology": ["tech", "technology", "ai", "digital", "internet", "software", "app", "cyber", "data", "computer", "phone", "smartphone"],
            "Entertainment": ["entertainment", "celebrity", "movie", "film", "music", "concert", "actor", "artist", "show", "tv", "series"],
            "Health": ["health", "medical", "hospital", "disease", "covid", "vaccine", "doctor", "healthcare", "patient", "treatment"],
            "Education": ["education", "school", "university", "student", "exam", "academic", "scholarship", "study", "learning"],
            "Environment": ["environment", "climate", "pollution", "flood", "weather", "disaster", "green", "carbon", "temperature"],
        }
        
        for category, words in keywords.items():
            if any(word in text for word in words):
                return category
        
        return "Other"
    
    def _detect_state(self, title: str, description: str) -> Optional[str]:
        """Detect Malaysia state from text."""
        from config import MALAYSIA_STATES
        text = (title + " " + description).lower()
        
        state_aliases = {
            "kl": "Kuala Lumpur",
            "kuala lumpur": "Kuala Lumpur",
            "selangor": "Selangor",
            "johor": "Johor",
            "jb": "Johor",
            "penang": "Pulau Pinang",
            "george town": "Pulau Pinang",
            "sabah": "Sabah",
            "sarawak": "Sarawak",
            "kuching": "Sarawak",
            "perak": "Perak",
            "ipoh": "Perak",
            "pahang": "Pahang",
            "kuantan": "Pahang",
            "kelantan": "Kelantan",
            "kota bharu": "Kelantan",
            "terengganu": "Terengganu",
            "melaka": "Melaka",
            "malacca": "Melaka",
            "negeri sembilan": "Negeri Sembilan",
            "seremban": "Negeri Sembilan",
            "kedah": "Kedah",
            "alor setar": "Kedah",
            "perlis": "Perlis",
            "putrajaya": "Putrajaya",
            "labuan": "Labuan",
        }
        
        for alias, state in state_aliases.items():
            if alias in text:
                return state
        
        for state in MALAYSIA_STATES:
            if state.lower() in text:
                return state
        
        return None
    
    def search_news(self, query: str, count: int = 5) -> List[Dict]:
        """Search for news using Brave Search API."""
        params = {
            "q": query,
            "count": count,
            "search_lang": "en",
            "freshness": "pd"  # Past day
        }
        
        try:
            response = requests.get(
                BRAVE_SEARCH_URL,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("results", [])
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching news for '{query}': {e}")
            return []
    
    def fetch_local_news(self) -> List[NewsArticle]:
        """Fetch Malaysia local news with AI summarization."""
        from config import LOCAL_SEARCH_QUERIES
        
        print("\n[LOCAL] Fetching Malaysia news...")
        articles = []
        seen_urls = set()
        texts_to_summarize = []
        raw_results = []
        
        # First pass: collect all results
        for query in LOCAL_SEARCH_QUERIES:
            if len(raw_results) >= MAX_NEWS_PER_CATEGORY:
                break
                
            results = self.search_news(query, count=3)
            
            for result in results:
                if len(raw_results) >= MAX_NEWS_PER_CATEGORY:
                    break
                    
                url = result.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                title = result.get("title", "No Title")
                description = result.get("description", "")
                
                # Combine title and description for summarization
                combined_text = f"{title}. {description}"
                texts_to_summarize.append(combined_text)
                raw_results.append(result)
        
        # Summarize all texts with AI
        if texts_to_summarize:
            print(f"\n[AI] Generating summaries for {len(texts_to_summarize)} articles...")
            summarizer = self._get_summarizer()
            summaries = summarizer.summarize_batch(texts_to_summarize, max_length=130, min_length=80)
        else:
            summaries = []
        
        # Create articles with AI summaries
        for i, (result, ai_summary) in enumerate(zip(raw_results, summaries)):
            url = result.get("url", "")
            title = result.get("title", "No Title")
            description = result.get("description", "")
            published = result.get("age", "Unknown")
            pub_datetime = parse_brave_age(published)

            # Extract thumbnail from Brave API
            thumbnail = result.get("thumbnail", {})
            image_url = thumbnail.get("src", "") if isinstance(thumbnail, dict) else ""

            # AI-generated full summary (~100 words)
            full_summary = ai_summary

            # Short snippet for collapsed view (first ~15 words)
            snippet_words = full_summary.split()[:15]
            snippet = " ".join(snippet_words) + "..."

            category = self._classify_category(title, description)
            state = self._detect_state(title, description) or "Malaysia"

            # Generate unique ID based on URL to avoid duplicates
            article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))[:8]
            now = datetime.now().isoformat()

            article = NewsArticle(
                id=article_id,
                title=title,
                summary=snippet,
                full_summary=full_summary,
                url=url,
                category=category,
                state=state,
                source=self._extract_source(url),
                published_date=published,  # Relative string for display (e.g. "2 hours ago")
                fetched_date=pub_datetime,  # Parsed publish datetime for sorting
                generated_date=now,  # When this article was generated in our system
                is_local=True,
                image_url=image_url,
                country="Malaysia",
            )
            articles.append(article)
            print(f"   [OK] {title[:50]}...")
        
        print(f"[OK] Fetched {len(articles)} local articles")
        return articles
    
    def fetch_global_news(self) -> List[NewsArticle]:
        """Fetch global/international news with AI summarization."""
        from config import GLOBAL_SEARCH_QUERIES
        
        print("\n[GLOBAL] Fetching Global news...")
        articles = []
        seen_urls = set()
        texts_to_summarize = []
        raw_results = []
        
        # First pass: collect all results
        for query in GLOBAL_SEARCH_QUERIES:
            if len(raw_results) >= MAX_NEWS_PER_CATEGORY:
                break
                
            results = self.search_news(query, count=3)
            
            for result in results:
                if len(raw_results) >= MAX_NEWS_PER_CATEGORY:
                    break
                    
                url = result.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                title = result.get("title", "No Title")
                description = result.get("description", "")
                
                # Combine title and description for summarization
                combined_text = f"{title}. {description}"
                texts_to_summarize.append(combined_text)
                raw_results.append(result)
        
        # Summarize all texts with AI
        if texts_to_summarize:
            print(f"\n[AI] Generating summaries for {len(texts_to_summarize)} articles...")
            summarizer = self._get_summarizer()
            summaries = summarizer.summarize_batch(texts_to_summarize, max_length=160, min_length=100)
        else:
            summaries = []
        
        # Create articles with AI summaries
        for i, (result, ai_summary) in enumerate(zip(raw_results, summaries)):
            url = result.get("url", "")
            title = result.get("title", "No Title")
            description = result.get("description", "")
            published = result.get("age", "Unknown")
            pub_datetime = parse_brave_age(published)

            # Extract thumbnail from Brave API
            thumbnail = result.get("thumbnail", {})
            image_url = thumbnail.get("src", "") if isinstance(thumbnail, dict) else ""

            # AI-generated full summary (~100 words)
            full_summary = ai_summary

            # Short snippet for collapsed view (first ~15 words)
            snippet_words = full_summary.split()[:15]
            snippet = " ".join(snippet_words) + "..."

            category = self._classify_category(title, description)

            # Detect country from source domain TLD
            country = self._detect_country_from_tld(url)

            # Generate unique ID based on URL to avoid duplicates
            article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))[:8]
            now = datetime.now().isoformat()

            article = NewsArticle(
                id=article_id,
                title=title,
                summary=snippet,
                full_summary=full_summary,
                url=url,
                category=category,
                state="Global",
                source=self._extract_source(url),
                published_date=published,  # Relative string for display (e.g. "2 hours ago")
                fetched_date=pub_datetime,  # Parsed publish datetime for sorting
                generated_date=now,  # When this article was generated in our system
                is_local=False,
                image_url=image_url,
                country=country,
            )
            articles.append(article)
            print(f"   [OK] {title[:50]}...")
        
        print(f"[OK] Fetched {len(articles)} global articles")
        return articles
    
    def fetch_all_news(self) -> List[NewsArticle]:
        """Fetch both local and global news with AI summarization."""
        local_news = self.fetch_local_news()
        global_news = self.fetch_global_news()
        
        all_news = local_news + global_news
        # Sort by fetched_date (estimated publish time, newest first)
        all_news.sort(key=lambda x: x.fetched_date, reverse=True)
        print(f"\n[TOTAL] {len(all_news)} articles ({len(local_news)} local, {len(global_news)} global)")
        
        return all_news
