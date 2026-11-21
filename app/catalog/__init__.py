from flask import Blueprint

catalog = Blueprint("catalog", __name__)

from app.catalog import routes  # noqa: E402,F401  (registers the views)
