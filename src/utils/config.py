"""Application configuration module.

Loads environment variables and provides centralized configuration
for the Rivers & Roots Analytics application.
"""
from pathlib import Path
from dotenv import load_dotenv
from enum import StrEnum
import os

load_dotenv()

class ENVIRONMENTS(StrEnum):
    """Enumeration of supported deployment environments.

    Members:
        DEVELOPMENT: Local development environment
        STAGING: Pre-production staging environment
        TESTING: Automated testing environment
        PRODUCTION: Live production environment
    """
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"

# Application settings
ENV = os.getenv('ENV', ENVIRONMENTS.DEVELOPMENT)

# Database connections
MONGO_URL = os.getenv('MONGO_URL')
REDIS_URL = os.getenv('REDIS_URL')

# Base directory paths
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
GOOGLE_APPLICATION_CREDENTIALS = os.path.join(BASE_DIR, os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''))
GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_RESOURCE_ID = os.getenv('GOOGLE_RESOURCE_ID')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')

# Data and storage paths
DATA_URL = os.getenv('DATA_URL', None)
UPLOAD_PATH = os.path.join(BASE_DIR, f"uploads_{ENV}")
DATA_DIR = os.path.join(BASE_DIR, "datasets")
VECTOR_DIR = os.path.join(BASE_DIR, "vectors")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# LLM configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')

# ---------------------------------------------------------------------------
# Game (simulation) configuration constants.
# Sourced from the Configuration Defaults table in README.md.
# ---------------------------------------------------------------------------
SHED_CAPACITY = 100
WEED_SPAWN_CHANCE = 0.005
TURNS_PER_DAY = 24
MAX_MARKET_ORDERS_PER_TURN = 10
EPISODE_STEPS = 720
STARTING_MONEY = 3000
BOARD_SIZE = 10

# Town building intervals (per README "Town Buildings" + Configuration Defaults).
TOWN_SHOP_UNLOCK_INTERVAL = 3   # days between successive shop unlocks
TOWN_SHOP_SELL_INTERVAL = 4     # turns between consumption ticks per unlocked shop
TOWN_CENTER_SELL_INTERVAL = 12  # turns between town-center consumption ticks
