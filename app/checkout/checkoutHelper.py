import json
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text

from app.checkout.calculatecart import calculate_cart
from app.checkout.commonutil import get_current_pending_cart
from app.extension import db
from app.models import Item, Product, Variant, VariantProduct

fetch_size_query = "select  \
   t.id, t.size, t.description  \
   from variant_product_rel trel \
   inner join variant t on t.id = trel.variant_id \
   where trel.product_id=:productId"


def fetchSizeForProduct(productId):
    rows = db.session.execute(text(fetch_size_query), {"productId": productId}).all()
    return json.dumps([list(row) for row in rows])


def updateVariantSize(itemId, sizeId, productId=None):
    """Switch a cart item to another size of the same product and reprice it.

    ``productId`` comes from the browser and is ignored: the price always comes
    from the item's own product, and the item must be in the current customer's
    pending cart.
    """
    cart = get_current_pending_cart()
    if not (cart and itemId and sizeId):
        return False
    item = db.session.query(Item).filter(Item.id == itemId, Item.cart_id == cart.first().id).first()
    if item is None:
        return False
    product = db.session.get(Product, item.product_id)
    variant = (
        db.session.query(Variant)
        .join(VariantProduct, VariantProduct.variant_id == Variant.id)
        .filter(VariantProduct.product_id == item.product_id, Variant.id == sizeId)
        .first()
    )
    if product is None or variant is None:
        return False
    item.size_id = variant.id
    item.product_price = (Decimal(str(product.sale_price)) * Decimal(str(variant.quantity))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    db.session.commit()
    calculate_cart()
    return True
