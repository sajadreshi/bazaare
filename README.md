# Bazaare

Bazaare is an online jewellery store built with Flask. It started as a copy of
[Folksy Cuisine](https://github.com/sajadreshi/FOLKSY-CUISINE), a food store,
and has been retargeted to jewellery. Launch scope is jewellery only; the data
model is generic enough to add apparel later as new categories and a new
collection.

## Stack

Python 3.12, Flask 3.1, SQLAlchemy 2.0 (Flask-SQLAlchemy) on PostgreSQL,
Flask-Admin 2, Flask-Login, Flask-WTF, Flask-Migrate (Alembic), Jinja
templates, Bootstrap.

Dependencies: `requirements.in` lists the direct ones; `requirements.txt` is
the fully pinned lock file generated from it with
`uv pip compile requirements.in -o requirements.txt --python-version 3.12`.

## Run locally

You need Python 3.12 and a running PostgreSQL.

```bash
createdb bazaare                      # or: psql -c "create database bazaare"
cp .env.example .env                  # set DATABASE_URL, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
python server.py                      # applies migrations, seeds data, serves on 127.0.0.1:8000
```

Open http://localhost:8000. The admin is at `/admin`; sign in with the
`ADMIN_EMAIL` / `ADMIN_PASSWORD` from your `.env`.

Configuration comes from the environment or a `.env` file:

| Variable                | Default / notes                                              |
| ----------------------- | ------------------------------------------------------------ |
| `DATABASE_URL`          | `postgresql://postgres@localhost:5432/bazaare`               |
| `SECRET_KEY`            | **required**; the app will not start without it              |
| `ADMIN_EMAIL`           | admin account created/updated on startup (skipped if unset)  |
| `ADMIN_PASSWORD`        | that account's password; change it and restart to reset it   |
| `FLASK_DEBUG`           | off; `1` enables the reloader and debugger (local use only)  |
| `HOST` / `PORT`         | `127.0.0.1` / `8000`                                         |
| `SESSION_COOKIE_SECURE` | off; set `1` when serving over HTTPS                         |

Useful commands:

```bash
flask --app server db upgrade                     # apply migrations
flask --app server db migrate -m "describe change" # after editing app/models.py
flask --app server seed                           # admin user + jewellery categories (safe to re-run)
```

## Development

```bash
ruff check . && ruff format .   # lint and format (config in pyproject.toml)
python -m pytest -q             # tests on in-memory SQLite
createdb bazaare_test && TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bazaare_test python -m pytest -q
```

`TEST_DATABASE_URL` must point at a throwaway database: its tables are dropped.
GitHub Actions runs ruff, the tests on SQLite and PostgreSQL 16, and a
migration upgrade/downgrade/upgrade on every pull request.

Every form POST needs a CSRF token: use `form.hidden_tag()` for WTForms or
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` in
hand-written forms. Flask-Admin adds the token to admin forms on its own.

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

### Carts and orders

- A **Cart** (with **Item** rows) is the shopper's working basket. Prices and
  totals are recalculated as items change.
- Placing an order turns the paid cart into an **Order** (`orders` table) with
  **OrderItem** rows. These copy the SKU, name, size, image and prices, and
  point at the shipping/billing addresses used. Later catalog edits don't
  rewrite past orders. The cart stays behind with status `COMPLETED`.
- Order status: `PLACED` → `SHIPPED` → `DELIVERED` (or `CANCELLED`).
  Admins change it under **Orders** in `/admin`, and customers see it under
  **Account → Orders**. Order numbers display as `BZ-000123`.
- Each relationship is stored once, in its link table: product↔variant
  (`variant_product_rel`), product↔category (`category_product_rel`),
  collection↔category (`collection_category_rel`), home page↔carousel
  (`home_carousel_rel`).

## Still to do

- Replace the food photos in `app/static/images/` with jewellery photography.
