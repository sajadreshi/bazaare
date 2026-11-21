import os

from flask_migrate import upgrade

from app import create_app
from app.config import env_flag
from app.seed import seed_all

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        upgrade()  # apply any pending migrations from migrations/versions
        seed_all()
    # Local-only and debug off by default. FLASK_DEBUG=1 turns on the reloader and the
    # interactive debugger (never expose that on a network); HOST=0.0.0.0 exposes the site.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        debug=env_flag("FLASK_DEBUG"),
    )
