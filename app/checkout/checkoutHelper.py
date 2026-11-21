from flask import session,jsonify
from sqlalchemy import text
from app.extension import db
from app.models import Variant, Item, Product
from decimal import Decimal,ROUND_HALF_UP
from app.checkout.calculatecart import calculate_cart
import json

fetch_size_query = "select  \
   t.id, t.size, t.description  \
   from variant_product_rel trel \
   inner join variant t on t.id = trel.variant_id \
   where trel.product_id=:productId"
   
   
   
def fetchSizeForProduct(productId):
   response = []
   value={"productId":productId} 
   sql = text(fetch_size_query)
   result = db.session.execute(sql,value) 
   if result.returns_rows == False:
      response = []
   else:
     for row in result.all():
       response.append(list(row))
     d = json.dumps(response)
     print(response)   
     return d
 
def updateVariantSize(itemId, sizeId, productId):
     if(itemId and sizeId and productId):
         produc_price = fetchProductPrice(productId)
         size_qty = fetchSizeDetails(sizeId)
         new_price = (Decimal(str(size_qty)) * Decimal(str(produc_price))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
         item = db.session.query(Item).filter(Item.id==itemId)
         item.update({"size_id":sizeId,"product_price":new_price})
         db.session.commit()
         calculate_cart()
         
         
         

def  fetchProductPrice(productId):
    productDetails = db.session.query(Product).filter(Product.id == productId).first()
    return productDetails.sale_price if productDetails else 0.00

def fetchSizeDetails(sizeId):
    sizeDetails = db.session.query(Variant).filter(Variant.id == sizeId).first()
    return sizeDetails.quantity if sizeDetails else 0