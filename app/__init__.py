import logging

import click
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_admin.menu import MenuLink
from flask_wtf.csrf import CSRFError

from app.adminapp.auth import bp as admin_auth_bp
from app.adminapp.views import (
    AttributesRelView,
    AttributesView,
    CarouselView,
    CategoryView,
    HolidayView,
    OrderView,
    ProductAssociationView,
    ProductView,
    RoleView,
    UserView,
    VariantView,
)
from app.auth import bp as auth_bp
from app.catalog import catalog as catalog_bp
from app.catalog_import import register as register_catalog_import
from app.checkout import checkout as checkout_bp
from app.customer import customer as customer_bp
from app.main import main
from app.services import catalog as catalog_service
from app.services import shipping as shipping_service
from app.services import wishlist as wishlist_service
from app.services.cart import item_count
from app.storage import init_storage
from app.webhooks import bp as webhooks_bp

from .config import Config
from .extension import admin, ckeditor, csrf, db, login_manager, mail, migrate
from .models import (
    Attribute,
    Carousel,
    Category,
    Holiday,
    Order,
    Product,
    ProductAssociation,
    ProductAttribute,
    Role,
    User,
    Variant,
)


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Add it to .env (see .env.example).")
    if not app.debug:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    db.init_app(app)
    login_manager.init_app(app)
    admin.init_app(app)
    migrate.init_app(app, db)
    ckeditor.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    init_storage(app)  # every POST (site and /admin) must carry a CSRF token

    @app.errorhandler(CSRFError)
    def csrf_failed(error):
        # A stale or missing form token: send them back to the form to try again
        # instead of showing a bare "Bad Request" page. Nothing was submitted.
        flash("That form had expired, so nothing was saved. Please try again.", "error")
        back = request.referrer
        if not (back and back.startswith(request.host_url)):
            back = url_for("main.home")
        return redirect(back)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.jinja_env.globals.update(
        cart_item_count=item_count,
        shop_menu=catalog_service.menu,
        wishlist_ids=wishlist_service.ids,
        is_on_sale=catalog_service.is_on_sale,
        primary_category=catalog_service.primary_category,
        shipping_method_for=shipping_service.method_for,
        shipping_estimate=shipping_service.estimated_delivery,
    )
    app.register_blueprint(main)
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(catalog_bp, url_prefix="/catalog")
    app.register_blueprint(checkout_bp, url_prefix="/checkout")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    admin.add_view(AttributesView(Attribute, db, category="Attributes"))
    admin.add_view(AttributesRelView(ProductAttribute, db, category="Attributes"))
    admin.add_view(CategoryView(Category, db, category="Category"))
    admin.add_view(CarouselView(Carousel, db, category="Content", name="Home banner slides"))
    admin.add_view(ProductView(Product, db, category="Product"))
    admin.add_view(VariantView(Variant, db, category="Product"))
    admin.add_view(UserView(User, db, category="User"))
    admin.add_view(RoleView(Role, db, category="User"))
    admin.add_view(ProductAssociationView(ProductAssociation, db, category="Attributes"))
    admin.add_view(HolidayView(Holiday, db, category="Holidays"))
    admin.add_view(OrderView(Order, db, name="Orders", endpoint="order"))
    if not any(link.name == "Sign out" for link in admin.menu_links()):
        admin.add_link(MenuLink(name="View shop", url="/"))
        admin.add_link(MenuLink(name="Sign out", url="/admin/logout"))

    register_catalog_import(app)

    @app.cli.command("seed")
    def seed_command():
        """Create the admin user and the starter jewellery catalog."""
        from app.seed import seed_all

        seed_all()
        click.echo("Seed data is in place.")

    return app
