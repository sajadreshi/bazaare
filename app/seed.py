"""Idempotent starter data for Bazaare.

Launch scope is jewellery only. Apparel can be added later by creating
new categories and a new collection in the admin.
"""

import logging

from flask import current_app

from app.extension import db
from app.models import Category, Collection, Role, User

log = logging.getLogger(__name__)

# The shop menu: (code, name, description, children, extra settings).
# Top-level entries are the main menu; children appear in its dropdown.
MENU = [
    (
        "NEW",
        "New Arrivals",
        "The latest pieces from our makers.",
        [
            ("NEW-JUST", "Just Launched", "Fresh from the workshop."),
            ("NEW-TRENDING", "Trending Now", "What everyone is wearing this season."),
        ],
    ),
    (
        "COLLECTIONS",
        "Collections",
        "Shop by craft and material.",
        [
            ("COLL-BRASS", "Brass", "Antique and matte gold-tone brass."),
            ("COLL-MEENAKARI", "Meenakari", "Hand-painted enamel in jewel colours."),
            ("COLL-SILVER", "Silver Look", "Oxidised silver-tone heritage designs."),
            ("COLL-PEARLS", "Pearls", "Pieces finished with faux pearls."),
            ("COLL-KUNDAN", "Kundan", "Kundan-style stone settings."),
        ],
    ),
    (
        "EARRINGS",
        "Earrings",
        "Jhumkas, chandbalis, studs and statement drops.",
        [
            ("EAR-JHUMKAS", "Jhumkas", "Bell-shaped classics."),
            ("EAR-CHANDBALIS", "Chandbalis", "Crescent-moon earrings."),
            ("EAR-STUDS", "Studs", "Everyday studs."),
            ("EAR-CUFFS", "Ear Cuffs", "No piercing needed."),
        ],
    ),
    (
        "NECKPIECES",
        "Neckpieces",
        "Haslis, necklaces and statement sets.",
        [
            ("NECK-HASLI", "Hasli", "Collars, torques and cord pendants."),
            ("NECK-NECKLACES", "Necklaces", "Pendants, chokers and necklace sets."),
            ("NECK-STATEMENT", "Statement Pieces", "Bold pieces for big occasions."),
        ],
    ),
    (
        "ACCESSORIES",
        "Accessories",
        "Bangles, rings and more.",
        [
            ("ACC-BANGLES", "Bangles", "Kadas, cuffs and bangle sets."),
            ("ACC-RINGS", "Rings", "Adjustable statement and everyday rings."),
            ("ACC-HAIR", "Hair Accessories", "Pins, combs and maang tikkas."),
        ],
    ),
    ("BESTSELLERS", "Bestsellers", "Our most-loved pieces.", []),
    (
        "GIFTING",
        "Gifting",
        "Thoughtful gifts for every budget.",
        [
            ("GIFT-UNDER-25", "Under $25", "Gifts at $25 or less.", {"max_price": 25}),
            ("GIFT-UNDER-50", "Under $50", "Gifts at $50 or less.", {"max_price": 50}),
            ("GIFT-SPECIAL", "Special Gifts", "Sets made for gifting."),
        ],
    ),
    (
        "SALE",
        "Sale",
        "Offers on selected pieces.",
        [
            ("SALE-FESTIVE", "Festive Offers", "Seasonal savings."),
            ("SALE-LAST", "Last Chance", "Final pieces at their lowest prices."),
        ],
    ),
]

# Categories from the first seed, before the menu existed; kept out of the menu.
LEGACY_CATEGORIES = ("RINGS", "NECKLACES", "BRACELETS")


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


def _upsert_category(code, name, description, parent, position, extra=None):
    """Create a menu category if missing. Existing ones keep any edits made in the admin,
    except that a missing parent or position is filled in."""
    category = Category.query.filter_by(code=code).first()
    if category is None:
        category = Category(code=code, name=name, description=description, is_active=True, **(extra or {}))
        db.session.add(category)
    if category.parent is None and parent is not None:
        category.parent = parent
    if not category.position:
        category.position = position
    return category


def seed_menu():
    top_level = []
    for position, (code, name, description, children) in enumerate(MENU, start=1):
        parent = _upsert_category(code, name, description, None, position)
        top_level.append(parent)
        for child_position, child in enumerate(children, start=1):
            child_code, child_name, child_description, *extra = child
            _upsert_category(child_code, child_name, child_description, parent, child_position, *extra)

    for legacy in Category.query.filter(Category.code.in_(LEGACY_CATEGORIES)):
        legacy.show_in_menu = False

    collection = Collection.query.filter_by(name="Jewellery").first()
    if not collection:
        collection = Collection(
            name="Jewellery", description="The BazaarE' jewellery collection.", is_active=True
        )
        db.session.add(collection)
    for category in top_level:
        if category not in collection.category:
            collection.category.append(category)
    db.session.commit()


def seed_all():
    seed_admin()
    seed_menu()
