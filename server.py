from flask_migrate import upgrade
from app import create_app
from app.seed import seed_all

app = create_app()

if __name__ == "__main__":
    app.debug = True
    with app.app_context():
        upgrade()   # apply any pending migrations from migrations/versions
        seed_all()
    app.run(host="0.0.0.0", port=8000)
