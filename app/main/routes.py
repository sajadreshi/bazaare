from flask import render_template

from app.main import main
from app.services.catalog import home_page


@main.route("/")
def home():
    return render_template("main/home.html", home=home_page())


@main.route("/about")
def about():
    return render_template("main/about.html")
