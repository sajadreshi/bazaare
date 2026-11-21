# Bazaare

Bazaare is an online jewellery store built with Flask. It started as a copy of
[Folksy Cuisine](https://github.com/sajadreshi/FOLKSY-CUISINE), a food store,
and has been retargeted to jewellery. Launch scope is jewellery only; the data
model is generic enough to add apparel later as new categories and a new
collection.

## Stack

Flask 2.3, Flask-SQLAlchemy (SQLite by default), Flask-Admin, Flask-Login,
Flask-Migrate, Jinja templates, Bootstrap.

## Run locally

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py          # creates bazaare.db, seeds admin + jewellery categories
```

Open http://localhost:8000. The admin is at `/admin`
(seeded login `user@admin.com` / `admin`, change it before going live).

Configuration comes from the environment:

| Variable       | Default               |
| -------------- | --------------------- |
| `SECRET_KEY`   | dev-only placeholder  |
| `DATABASE_URL` | `sqlite:///bazaare.db` |

## Tests

```bash
pip install pytest && python -m pytest -q
```

## Domain model (renamed from Folksy Cuisine)

| Folksy Cuisine                    | Bazaare                                   |
| --------------------------------- | ----------------------------------------- |
| `Menu` / `menu`                   | `Collection` / `collection`               |
| `menu_category_rel`               | `collection_category_rel`                 |
| `Tray` / `tray` (portion sizes)   | `Variant` / `variant` (ring size, length) |
| `tray_product_rel`, `tray_id`     | `variant_product_rel`, `variant_id`       |
| `tray_image`                      | `variant_image`                           |
| `is_vegeterian`, `is_vegan`       | `is_handmade`, `is_sustainable`           |
| (none)                            | `material` (e.g. sterling silver, 18k gold) |
| `folksy.db`                       | `bazaare.db`                              |

Seeded catalog: a **Jewellery** collection with Rings, Necklaces, Earrings and
Bracelets categories.

## Still to do

- Replace the food photos in `app/static/images/` with jewellery photography.
