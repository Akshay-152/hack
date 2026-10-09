"""Application configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central config; secrets come from .env, never the source tree."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # "memory" for built-in dev storage, "firestore" for real Firebase.
    DB_BACKEND = os.getenv("DB_BACKEND", "memory")
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

    # Server-side CORS: the frontend origin that may call this API.
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")

    # Recommendation scoring weights (PLAN section 6.3), tunable without code changes.
    WEIGHT_CATEGORY_MATCH = 3
    WEIGHT_TAG_MATCH = 2
    WEIGHT_AUDIENCE_RELEVANCE = 1
    WEIGHT_REGISTRATION_OPEN = 1
