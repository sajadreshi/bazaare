import os

from flask_migrate import upgrade

from app import create_app
from app.seed import seed_all

app = create_app()

if __name__ == "__main__":
    app.debug = True
    with app.app_context():
        upgrade()  # apply any pending migrations from migrations/versions
        seed_all()
    # Local-only by default; set HOST=0.0.0.0 to expose on your network.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8000)))
