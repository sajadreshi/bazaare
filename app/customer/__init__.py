from flask import Blueprint

customer = Blueprint("customer", __name__)

from app.customer import routes  # noqa: E402,F401  (registers the views)
