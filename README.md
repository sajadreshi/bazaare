# Bazaare

Bazaare is an online jewellery store built with Flask. It started as a copy of
[Folksy Cuisine](https://github.com/sajadreshi/FOLKSY-CUISINE), a food store,
and has been retargeted to jewellery. Launch scope is jewellery only; the data
model is generic enough to add apparel later as new categories and a new
collection.

## Stack

Flask 2.3, Flask-SQLAlchemy on PostgreSQL, Flask-Admin, Flask-Login,
Flask-Migrate (Alembic), Jinja templates, Bootstrap.

## Run locally

You need Python 3.12 and a running PostgreSQL.

```bash
createdb bazaare                      # or: psql -c "create database bazaare"
cp .env.example .env                  # then set DATABASE_URL for your Postgres user/password
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py                      # applies migrations, seeds data, serves on :8000
```

Open http://localhost:8000. The admin is at `/admin`
(seeded login `user@admin.com` / `admin`, change it before going live).

Configuration comes from the environment or a `.env` file:

| Variable       | Default                                        |
| -------------- | ---------------------------------------------- |
| `DATABASE_URL` | `postgresql://postgres@localhost:5432/bazaare` |
| `SECRET_KEY`   | dev-only placeholder                           |

Useful commands:

```bash
flask --app server db upgrade                     # apply migrations
flask --app server db migrate -m "describe change" # after editing app/models.py
flask --app server seed                           # admin user + jewellery categories (safe to re-run)
```

## Tests

Tests use in-memory SQLite by default. To run them against Postgres, point
`TEST_DATABASE_URL` at a throwaway database (its tables are dropped):

```bash
pip install pytest
python -m pytest -q
createdb bazaare_test && TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bazaare_test python -m pytest -q
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
