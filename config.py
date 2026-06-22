"""Configuration settings for News Curator app."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/news/search"

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
#OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_MODEL = "openai/gpt-oss-120b"  # Alternative model for testing

# App Configuration
MAX_NEWS_PER_CATEGORY = 5  # Limit to 5 news per category for testing
DATA_FILE = "news_data.json"

# Categories for classification
CATEGORIES = [
    "Politics", "Crime", "Economy", "Sports", 
    "Entertainment", "Technology", "Health", "Education",
    "Environment", "International", "Other"
]

# Malaysia states for local news classification
MALAYSIA_STATES = [
    "Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan",
    "Pahang", "Perak", "Perlis", "Pulau Pinang", "Sabah",
    "Sarawak", "Selangor", "Terengganu", "Kuala Lumpur",
    "Putrajaya", "Labuan"
]

# Search queries for different categories
LOCAL_SEARCH_QUERIES = [
    "Malaysia news today",
    "Malaysia politics",
    "Malaysia economy",
    "Kuala Lumpur news",
    "Selangor news"
]

GLOBAL_SEARCH_QUERIES = [
    "World news today",
    "International politics",
    "Global economy",
    "World technology",
    "International sports"
]
