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

    # Image uploads: Cloudflare R2 when all five R2_* settings are set, otherwise a
    # local folder (UPLOAD_DIR, default instance/uploads) served at /media/.
    R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
    R2_BUCKET = os.environ.get("R2_BUCKET")
    R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # reject request bodies (uploads) over 16 MB

    # Shipping labels through Shippo (https://goshippo.com). Without a key, the admin
    # enters carrier + tracking number by hand when marking an order shipped.
    SHIPPO_API_KEY = os.environ.get("SHIPPO_API_KEY")
    # Secret added to the tracking-webhook URL (?token=...) so only Shippo can post updates.
    SHIPPO_WEBHOOK_TOKEN = os.environ.get("SHIPPO_WEBHOOK_TOKEN")
    SHIP_FROM = {
        "name": os.environ.get("SHIP_FROM_NAME", ""),
        "company": os.environ.get("SHIP_FROM_COMPANY", "BazaarE'"),
        "street1": os.environ.get("SHIP_FROM_STREET1", ""),
        "street2": os.environ.get("SHIP_FROM_STREET2", ""),
        "city": os.environ.get("SHIP_FROM_CITY", ""),
        "state": os.environ.get("SHIP_FROM_STATE", ""),
        "zip": os.environ.get("SHIP_FROM_ZIP", ""),
        "country": "US",
        "phone": os.environ.get("SHIP_FROM_PHONE", ""),
        "email": os.environ.get("SHIP_FROM_EMAIL", ""),
    }
    # Default parcel: a padded jewellery mailer. Override with SHIP_PARCEL="L,W,H,weight_oz".
    SHIP_PARCEL = os.environ.get("SHIP_PARCEL", "9,6,1,4")

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
