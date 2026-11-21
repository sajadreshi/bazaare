"""Idempotent starter data for Bazaare.

Launch scope is jewellery only. Apparel can be added later by creating
new categories and a new collection in the admin.
"""
from werkzeug.security import generate_password_hash
from app.extension import db
from app.models import User, Role, Category, Collection

JEWELLERY_CATEGORIES = [
    ("RINGS", "Rings", "Everyday and statement rings."),
    ("NECKLACES", "Necklaces", "Chains, pendants and chokers."),
    ("EARRINGS", "Earrings", "Studs, hoops and drops."),
    ("BRACELETS", "Bracelets", "Bangles, cuffs and charm bracelets."),
]


def seed_admin():
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)
        db.session.commit()

    admin_user = User.query.filter_by(email="user@admin.com").first()
    if not admin_user:
        admin_user = User(
            email="user@admin.com",
            first_name="admin",
            last_name="user",
            password=generate_password_hash("admin"),
            is_admin=True,
        )
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created with ADMIN role")


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
        collection = Collection(name="Jewellery", description="The Bazaare jewellery collection.", is_active=True)
        db.session.add(collection)
    for category in categories:
        if category not in collection.category:
            collection.category.append(category)
    db.session.commit()


def seed_all():
    seed_admin()
    seed_jewellery_catalog()
