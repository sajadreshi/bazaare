"""Incoming webhooks from outside services (no CSRF token; authenticated by a shared secret)."""

import hmac
import logging

from flask import Blueprint, abort, current_app, jsonify, request

from app.extension import csrf
from app.services import shippo

log = logging.getLogger(__name__)

bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


@bp.route("/shippo", methods=["POST"])
@csrf.exempt
def shippo_tracking():
    """Shippo tracking updates. Register this URL in Shippo with ?token=<SHIPPO_WEBHOOK_TOKEN>."""
    expected = current_app.config.get("SHIPPO_WEBHOOK_TOKEN")
    given = request.args.get("token", "")
    if not expected or not hmac.compare_digest(given, expected):
        abort(403)
    payload = request.get_json(silent=True) or {}
    order = shippo.handle_tracking_update(payload)
    return jsonify(ok=True, order=order.number if order else None)
