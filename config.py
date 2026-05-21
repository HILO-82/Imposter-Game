import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'imposter.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_NAME_LENGTH = 50
    MAX_CLUE_LENGTH = 100
