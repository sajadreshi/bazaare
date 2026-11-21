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


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config(object):
    # No fallback: a guessable key would let anyone forge login sessions.
    # create_app() refuses to start without it (tests pass their own).
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 25))
    ADMINS = [os.environ.get("MAIL_SENDER", "no-reply@bazaare.local")]

    # The seeded admin account. Nothing is created unless both are set.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # CSRF tokens stay valid for the whole browser session (Flask-WTF's default is
    # one hour, which broke forms left open, e.g. the admin sign-in page).
    WTF_CSRF_TIME_LIMIT = None

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE")
