"""Idempotent starter data for Bazaare.

Launch scope is jewellery only. Apparel can be added later by creating
new categories and a new collection in the admin.
"""

import logging

from flask import current_app

from app.extension import db
from app.models import Category, Collection, Role, User

log = logging.getLogger(__name__)

JEWELLERY_CATEGORIES = [
    ("RINGS", "Rings", "Everyday and statement rings."),
    ("NECKLACES", "Necklaces", "Chains, pendants and chokers."),
    ("EARRINGS", "Earrings", "Studs, hoops and drops."),
    ("BRACELETS", "Bracelets", "Bangles, cuffs and charm bracelets."),
]


def seed_admin():
    """Create or update the admin account from ADMIN_EMAIL / ADMIN_PASSWORD.

    The environment is the source of truth: changing ADMIN_PASSWORD and
    restarting resets that account's password.
    """
    email = current_app.config.get("ADMIN_EMAIL")
    password = current_app.config.get("ADMIN_PASSWORD")
    if not email or not password:
        log.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set; no admin account was created or updated.")
        return

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)

    admin_user = User.query.filter_by(email=email).first()
    if not admin_user:
        admin_user = User(email=email, first_name="Admin", last_name="User", is_admin=True)
        admin_user.set_password(password)
        db.session.add(admin_user)
        log.info("Created admin user %s", email)
    elif not admin_user.check_password(password):
        admin_user.set_password(password)
        log.info("Updated password for admin user %s", email)
    admin_user.is_admin = True
    if admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
    db.session.commit()


def seed_jewellery_catalog():
    categories = []
    for code, name, description in JEWELLERY_CATEGORIES:
        category = Category.query.filter_by(code=code).first()
        if not category:
            category = Category(code=code, name=name, description=description, is_active=True)
            db.session.add(category)
        categories.append(category)

    collection = Collection.query.filter_by(name="Jewellery").first()
    if not collection:
        collection = Collection(
            name="Jewellery", description="The Bazaare jewellery collection.", is_active=True
        )
        db.session.add(collection)
    for category in categories:
        if category not in collection.category:
            collection.category.append(category)
    db.session.commit()


def seed_all():
    seed_admin()
    seed_jewellery_catalog()
