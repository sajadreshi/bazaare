from flask import Blueprint

checkout = Blueprint("checkout", __name__)

from app.checkout import routes  # noqa: E402,F401  (registers the views)
