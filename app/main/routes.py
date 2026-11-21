from flask import render_template
from sqlalchemy import text

from app.extension import db
from app.main import main
from app.main.homepagebuilder import build_home_page, s_query


@main.route("/")
def home():
    sql = text(s_query)
    result = db.session.execute(sql)
    home = build_home_page(result)
    return render_template("main/home.html", home=home)


@main.route("/about")
def about():
    return render_template("main/about.html")
