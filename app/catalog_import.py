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
from app.models import (
    Attribute,
    Category,
    Product,
    ProductAssociation,
    ProductAttribute,
    ProductImage,
    Variant,
)
from app.storage import save_image

log = logging.getLogger(__name__)

ONE_SIZE = "One Size"


def _upload(images_dir, filename, folder):
    path = os.path.join(images_dir, filename)
    with open(path, "rb") as fh:
        return save_image(FileStorage(stream=fh, filename=filename), folder)


def _set_designs(product, designs):
    """Give the product one option per design (or a single One Size option). Stock is left as it was."""
    wanted = [name[:64] for name in designs] or [ONE_SIZE]
    current = {v.name: v for v in product.options}
    product.options = [
        current.get(name) or Variant(name=name, is_default=position == 0)
        for position, name in enumerate(wanted)
    ]
    for position, variant in enumerate(product.options):
        variant.position = position
    product.option_label = "Design" if designs else None


def _set_attributes(product, values):
    """Product details from the manifest, e.g. {"Stone": "Moonstone", "Finish": "Oxidised"}."""
    current = {link.attribute.name: link for link in product.attribute_links}
    for name, value in values.items():
        if name in current:
            current[name].value = str(value)
            continue
        attribute = Attribute.query.filter_by(name=name).first()
        if attribute is None:
            attribute = Attribute(name=name)
            db.session.add(attribute)
        product.attribute_links.append(ProductAttribute(attribute=attribute, value=str(value)))


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
        product.price = price
        compare_at = item.get("compare_at")
        product.compare_at_price = Decimal(str(compare_at)) if compare_at else None
        product.is_active = True
        product.categories = [categories[code] for code in item["categories"]]
        _set_designs(product, item.get("designs"))
        _set_attributes(product, item.get("attributes") or {})
        if not product.images:
            product.images = [
                ProductImage(image=_upload(images_dir, filename, "products"), position=position)
                for position, filename in enumerate(item["images"])
            ]
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
