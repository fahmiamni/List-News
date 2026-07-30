"""News fetcher using Brave Search API — no local AI, parallel HTTP calls."""
import requests
import uuid
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse
from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, MAX_NEWS_PER_CATEGORY
from models import NewsArticle


def parse_brave_age(age_str: str, reference: datetime = None) -> str:
    """Parse Brave Search API 'age' field (e.g. '6h ago', '2d ago') into ISO datetime."""
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
    """Fetches news from Brave Search API — no local AI, uses Brave description directly."""

    def __init__(self):
        self.api_key = BRAVE_API_KEY
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        })

    def _extract_source(self, url: str) -> str:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")

    def _detect_country_from_tld(self, url: str) -> str:
        domain = urlparse(url).netloc
        parts = domain.split(".")
        tld = parts[-1].lower() if len(parts) > 1 else ""

        special_coms = {"co", "com", "org", "net", "gov", "edu", "ac"}
        if len(parts) >= 3 and parts[-2].lower() in special_coms:
            tld = parts[-2].lower() + "." + tld
        elif tld in special_coms and len(parts) >= 3:
            tld = parts[-1].lower() + "." + parts[-2].lower()

        tld_map = {
            "my": "Malaysia", "sg": "Singapore", "id": "Indonesia",
            "th": "Thailand", "ph": "Philippines", "vn": "Vietnam",
            "cn": "China", "hk": "Hong Kong", "tw": "Taiwan",
            "jp": "Japan", "kr": "South Korea", "in": "India",
            "pk": "Pakistan", "bd": "Bangladesh", "lk": "Sri Lanka",
            "au": "Australia", "nz": "New Zealand", "uk": "UK",
            "co.uk": "UK", "fr": "France", "de": "Germany",
            "it": "Italy", "es": "Spain", "pt": "Portugal",
            "nl": "Netherlands", "be": "Belgium", "ch": "Switzerland",
            "at": "Austria", "se": "Sweden", "no": "Norway",
            "dk": "Denmark", "fi": "Finland", "pl": "Poland",
            "cz": "Czech Republic", "ru": "Russia", "br": "Brazil",
            "mx": "Mexico", "ar": "Argentina", "cl": "Chile",
            "za": "South Africa", "ng": "Nigeria", "ke": "Kenya",
            "eg": "Egypt", "ae": "UAE", "sa": "Saudi Arabia",
            "il": "Israel", "tr": "Turkey", "ie": "Ireland",
            "ca": "Canada",
        }
        return tld_map.get(tld, "")

    def _classify_category(self, title: str, description: str) -> str:
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
        from config import MALAYSIA_STATES
        text = (title + " " + description).lower()
        state_aliases = {
            "kl": "Kuala Lumpur", "kuala lumpur": "Kuala Lumpur",
            "selangor": "Selangor", "johor": "Johor", "jb": "Johor",
            "penang": "Pulau Pinang", "george town": "Pulau Pinang",
            "sabah": "Sabah", "sarawak": "Sarawak", "kuching": "Sarawak",
            "perak": "Perak", "ipoh": "Perak", "pahang": "Pahang",
            "kuantan": "Pahang", "kelantan": "Kelantan",
            "kota bharu": "Kelantan", "terengganu": "Terengganu",
            "melaka": "Melaka", "malacca": "Melaka",
            "negeri sembilan": "Negeri Sembilan", "seremban": "Negeri Sembilan",
            "kedah": "Kedah", "alor setar": "Kedah", "perlis": "Perlis",
            "putrajaya": "Putrajaya", "labuan": "Labuan",
        }
        for alias, state in state_aliases.items():
            if alias in text:
                return state
        for state in MALAYSIA_STATES:
            if state.lower() in text:
                return state
        return None

    def search_news(self, query: str, count: int = 5) -> List[Dict]:
        params = {
            "q": query,
            "count": count,
            "search_lang": "en",
            "freshness": "pd"
        }
        try:
            response = self._session.get(
                BRAVE_SEARCH_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching news for '{query}': {e}")
            return []

    def _search_news_parallel(self, queries: List[str], max_results: int) -> List[Dict]:
        all_results = []
        seen_urls = set()

        with ThreadPoolExecutor(max_workers=min(len(queries), 8)) as executor:
            futures = {executor.submit(self.search_news, q, count=3): q for q in queries}
            for future in as_completed(futures):
                results = future.result()
                for result in results:
                    if len(all_results) >= max_results:
                        break
                    url = result.get("url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    all_results.append(result)

        return all_results[:max_results]

    def _make_article(self, result: dict, is_local: bool) -> NewsArticle:
        url = result.get("url", "")
        title = result.get("title", "No Title")
        description = result.get("description", "")
        published = result.get("age", "Unknown")
        pub_datetime = parse_brave_age(published)

        thumbnail = result.get("thumbnail", {})
        image_url = thumbnail.get("src", "") if isinstance(thumbnail, dict) else ""

        full_summary = description
        snippet_words = full_summary.split()[:15]
        snippet = " ".join(snippet_words) + "..." if snippet_words else ""

        category = self._classify_category(title, description)
        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))[:8]
        now = datetime.now().isoformat()

        if is_local:
            state = self._detect_state(title, description) or "Malaysia"
            country = "Malaysia"
        else:
            state = "Global"
            country = self._detect_country_from_tld(url)

        return NewsArticle(
            id=article_id,
            title=title,
            summary=snippet,
            full_summary=full_summary,
            url=url,
            category=category,
            state=state,
            source=self._extract_source(url),
            published_date=published,
            fetched_date=pub_datetime,
            generated_date=now,
            is_local=is_local,
            image_url=image_url,
            country=country,
        )

    def fetch_local_news(self) -> List[NewsArticle]:
        from config import LOCAL_SEARCH_QUERIES
        print("\n[LOCAL] Fetching Malaysia news...")
        raw_results = self._search_news_parallel(LOCAL_SEARCH_QUERIES, MAX_NEWS_PER_CATEGORY)
        articles = [self._make_article(r, is_local=True) for r in raw_results]
        for a in articles:
            print(f"   [OK] {a.title[:50]}...")
        print(f"[OK] Fetched {len(articles)} local articles")
        return articles

    def fetch_global_news(self) -> List[NewsArticle]:
        from config import GLOBAL_SEARCH_QUERIES
        print("\n[GLOBAL] Fetching Global news...")
        raw_results = self._search_news_parallel(GLOBAL_SEARCH_QUERIES, MAX_NEWS_PER_CATEGORY)
        articles = [self._make_article(r, is_local=False) for r in raw_results]
        for a in articles:
            print(f"   [OK] {a.title[:50]}...")
        print(f"[OK] Fetched {len(articles)} global articles")
        return articles

    def fetch_all_news(self) -> List[NewsArticle]:
        local_news = self.fetch_local_news()
        global_news = self.fetch_global_news()
        all_news = local_news + global_news
        all_news.sort(key=lambda x: x.fetched_date, reverse=True)
        print(f"\n[TOTAL] {len(all_news)} articles ({len(local_news)} local, {len(global_news)} global)")
        return all_news