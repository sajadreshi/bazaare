import os
import os.path as op
from flask import Flask,  url_for, redirect, request
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, BaseView
from flask_admin.form import SecureForm
from .config import Config

from .extension import db, login_manager, admin, migrate, ckeditor,mail
from .models import User, Attribute, ProductAttribute, Category,Collection
from .models import Carousal,HomePageContent,Product, Variant, Role, ProductAssociation,Holiday
from app.main import main
from app.adminapp.views import  AttributesView, AttributesRelView, CategoryView, CollectionView, ProductAssociationView
from app.adminapp.views import HomePageView,CarousalView,ProductView, VariantView, UserView, RoleView,HolidayView
from app.errors import bp as error_bp
from app.auth import bp as auth_bp
from app.catalog import catalog as catalog_bp
from app.checkout import checkout as checkout_bp
from app.customer import customer as customer_bp
from app.checkout.cartcounthelper import get_cart_count

def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    db.init_app(app)
    login_manager.init_app(app)
    admin.init_app(app)
    migrate.init_app(app,db)
    ckeditor.init_app(app)
    mail.init_app(app)
    @login_manager.user_loader
    
    def load_user(user_id):
        return User.query.get(user_id)
    app.jinja_env.globals.update(cart_count=get_cart_count)
    app.register_blueprint(main)
    app.register_blueprint(error_bp,url_prefix="/error")
    app.register_blueprint(auth_bp,url_prefix="/auth")
    app.register_blueprint(catalog_bp,url_prefix="/catalog")
    app.register_blueprint(checkout_bp,url_prefix="/checkout")
    app.register_blueprint(customer_bp,url_prefix="/customer")
    admin.add_view(AttributesView(Attribute, db.session, category="Attributes"))
    admin.add_view(AttributesRelView(ProductAttribute, db.session, category="Attributes"))
    admin.add_view(CategoryView(Category, db.session, category="Category"))
    admin.add_view(CollectionView(Collection, db.session, category="Category"))
    admin.add_view(CarousalView(Carousal, db.session, category="Content"))
    admin.add_view(HomePageView(HomePageContent, db.session, category="Content"))
    admin.add_view(ProductView(Product, db.session, category="Product"))
    admin.add_view(VariantView(Variant, db.session, category="Product"))
    admin.add_view(UserView(User, db.session,  category="User"))
    admin.add_view(RoleView(Role, db.session,  category="User"))
    admin.add_view(ProductAssociationView(ProductAssociation, db.session, category="Attributes"))
    admin.add_view(HolidayView(Holiday, db.session, category="Holidays"))
    return app

