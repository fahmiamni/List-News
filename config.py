"""Configuration settings for News Curator app."""
import os
from dotenv import load_dotenv

load_dotenv()

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/news/search"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"

MAX_NEWS_PER_CATEGORY = 5
DATA_FILE = "news_data.json"

CATEGORIES = [
    "Politics", "Crime", "Economy", "Sports",
    "Entertainment", "Technology", "Health", "Education",
    "Environment", "International", "Other"
]

MALAYSIA_STATES = [
    "Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan",
    "Pahang", "Perak", "Perlis", "Pulau Pinang", "Sabah",
    "Sarawak", "Selangor", "Terengganu", "Kuala Lumpur",
    "Putrajaya", "Labuan"
]

LOCAL_SEARCH_QUERIES = [
    "Malaysia news today",
    "Malaysia politics economy",
    "Kuala Lumpur Selangor news",
]

GLOBAL_SEARCH_QUERIES = [
    "World news today",
    "International politics economy",
    "World technology sports",
]