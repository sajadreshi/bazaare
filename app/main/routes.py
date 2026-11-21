import pprint
from werkzeug.urls import url_parse
from flask import render_template, request, redirect, url_for, session, flash, Blueprint
from flask_login import login_required, current_user
from sqlalchemy import text
from app.main import main
from app.extension import db
from app.main.homepagebuilder import s_query, build_home_page
from app.models import User



@main.route("/")
def home():  
    sql = text(s_query)
    result = db.session.execute(sql)
    print("result ", result)
    home = build_home_page(result)
    pprint.pprint(home)       
    return render_template("main/home.html",home=home)

@main.route("/about")
def about():
   
    return render_template("main/about.html")