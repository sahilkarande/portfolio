import os
from pathlib import Path

from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_uri():
    """Resolve the database URL.

    Priority:
      1. DATABASE_URL  (full SQLAlchemy URL)
      2. MYSQL_USER / MYSQL_PASSWORD / MYSQL_HOST / MYSQL_DB  (PythonAnywhere style;
         built with URL.create so passwords with special characters are safe)
      3. Local SQLite file in instance/portfolio.db
    """
    if url := os.getenv("DATABASE_URL"):
        return url
    if os.getenv("MYSQL_HOST"):
        return URL.create(
            "mysql+pymysql",
            username=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT")) if os.getenv("MYSQL_PORT") else None,
            database=os.getenv("MYSQL_DB"),
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)
    return f"sqlite:///{BASE_DIR / 'instance' / 'portfolio.db'}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # PythonAnywhere's MySQL closes idle connections after ~300s.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

    # Uploaded files live under static/uploads/<kind>/
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB per request

    # Mail (Gmail SMTP works on PythonAnywhere free accounts)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
    MAIL_USERNAME = os.getenv("EMAIL_ADDRESS")
    MAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    OWNER_EMAIL = os.getenv("OWNER_EMAIL")
    SITE_URL = os.getenv("SITE_URL", "")

    ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "1") == "1"
    ANALYTICS_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "395"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    # TEST_DATABASE_URL lets the suite run against MySQL too (e.g. a throwaway Docker container).
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite://")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True} if os.getenv("TEST_DATABASE_URL") else {}
    WTF_CSRF_ENABLED = False


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
