import os

from dotenv import load_dotenv

# Load a local .env file if present (see .env.example). Real env vars win.
load_dotenv()


def _database_url():
    url = os.environ.get("DATABASE_URL") or "postgresql://postgres@localhost:5432/bazaare"
    # Some hosts (Railway, Heroku) hand out postgres://, which SQLAlchemy 2 rejects.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-change-me"
    SQLALCHEMY_DATABASE_URI = _database_url()
    FLASK_ADMIN_SWATCH = "cyborg"
    MAIL_SERVER = "localhost"
    MAIL_PORT = "25"
    ADMINS = ["your-email@example.com"]
