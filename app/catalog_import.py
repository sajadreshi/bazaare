"""Import products (and their photos) from a JSON manifest such as data/catalog/products.json.

    flask --app server import-catalog data/catalog/products.json --images ~/Documents/bazaare_images

Products are matched by SKU, so running it again skips what's already there
(``--update`` refreshes text, prices, categories and designs instead). Photos
are uploaded to the configured storage (R2 or the local fallback) only when a
product has none yet.
"""

import json
import logging
import os
from decimal import Decimal

import click
from flask import current_app
from werkzeug.datastructures import FileStorage

from app.extension import db
from app.models import Category, Product, ProductAssociation, Variant
from app.storage import save_image

log = logging.getLogger(__name__)

IMAGE_FIELDS = ("main_image", "alt1_image", "alt2_image", "alt3_image")
ONE_SIZE = "One Size"


def _upload(images_dir, filename, folder):
    path = os.path.join(images_dir, filename)
    with open(path, "rb") as fh:
        return save_image(FileStorage(stream=fh, filename=filename), folder)


def _one_size_variant():
    variant = Variant.query.filter_by(size=ONE_SIZE).first()
    if variant is None:
        variant = Variant(size=ONE_SIZE, quantity=1, is_default=True, description="")
        db.session.add(variant)
    return variant


def _set_designs(product, designs):
    """Give the product one variant per design (or the shared One Size variant)."""
    wanted = designs or [ONE_SIZE]
    current = {v.size: v for v in product.variant}
    for variant in list(product.variant):
        if variant.size not in wanted:
            variant.products.remove(product)
    for position, name in enumerate(wanted):
        if name in current:
            continue
        if name == ONE_SIZE:
            variant = _one_size_variant()
        else:
            variant = Variant(size=name[:30], quantity=1, is_default=position == 0, description="Design")
            db.session.add(variant)
        variant.products.append(product)


def _import_associations(links):
    """Add related-product links ({source, target, type, position}) that don't exist yet."""
    skus = {sku for link in links for sku in (link["source"], link["target"])}
    products = {p.sku: p for p in Product.query.filter(Product.sku.in_(skus))} if skus else {}
    added = 0
    for link in links:
        source, target = products.get(link["source"]), products.get(link["target"])
        if source is None or target is None:
            raise click.ClickException(f"related link {link['source']} -> {link['target']}: unknown SKU")
        kind = link.get("type", "XSELL")
        exists = ProductAssociation.query.filter_by(
            source_product_id=source.id, target_product_id=target.id, association_type=kind
        ).first()
        if exists is None:
            db.session.add(
                ProductAssociation(
                    source_product_id=source.id,
                    target_product_id=target.id,
                    association_type=kind,
                    position=link.get("position", 0),
                    is_active=True,
                )
            )
            added += 1
    db.session.commit()
    return added


def import_catalog(manifest_path, images_dir, update=False):
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    categories = {c.code: c for c in Category.query.all()}
    created = updated = skipped = 0

    for item in manifest["products"]:
        missing = [code for code in item["categories"] if code not in categories]
        if missing:
            raise click.ClickException(
                f"{item['sku']}: unknown categories {missing} (run `flask seed` first)"
            )
        product = Product.query.filter_by(sku=item["sku"]).first()
        if product is not None and not update:
            skipped += 1
            continue
        is_new = product is None
        if is_new:
            product = Product(sku=item["sku"])
            db.session.add(product)
        price = Decimal(str(item["price"]))
        product.name = item["name"]
        product.description = item["description"]
        product.material = item.get("material")
        product.sale_price = price
        product.retail_price = Decimal(str(item.get("compare_at") or price))
        product.is_active = True
        product.display = True
        product.categories = [categories[code] for code in item["categories"]]
        _set_designs(product, item.get("designs"))
        if not product.main_image:
            for field, filename in zip(IMAGE_FIELDS, item["images"], strict=False):
                setattr(product, field, _upload(images_dir, filename, "products"))
        db.session.commit()
        created += is_new
        updated += not is_new
        click.echo(f"{'created' if is_new else 'updated'} {product.sku}  {product.name}")

    links_added = _import_associations(manifest.get("associations", []))
    if links_added:
        click.echo(f"{links_added} related-product links added")

    for code, filename in manifest.get("banners", {}).items():
        category = categories.get(code)
        if category is not None and (update or not category.banner_image):
            category.banner_image = _upload(images_dir, filename, "banners")
            db.session.commit()
            click.echo(f"banner for {code}")
    return created, updated, skipped


def register(app):
    @app.cli.command("import-catalog")
    @click.argument("manifest", type=click.Path(exists=True, dir_okay=False))
    @click.option("--images", "images_dir", required=True, type=click.Path(exists=True, file_okay=False))
    @click.option("--update", is_flag=True, help="Refresh products that already exist (photos are kept).")
    def import_catalog_command(manifest, images_dir, update):
        """Import products and photos from a JSON manifest."""
        storage = current_app.extensions["storage"]
        click.echo(f"Uploading photos to: {storage.kind}")
        created, updated, skipped = import_catalog(manifest, images_dir, update=update)
        click.echo(f"Done: {created} created, {updated} updated, {skipped} already there.")
