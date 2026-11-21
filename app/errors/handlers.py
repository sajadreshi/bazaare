from flask import render_template

from app.errors import bp


@bp.errorhandler(404)
def not_found_error(error):
    render_template("templates/errors/404.html"), 400


@bp.errorhandler(500)
def not_found_error(error):
    render_template("templates/errors/500.html"), 500
