from flask import session
from sqlalchemy import text
from app.extension import db
from app.checkout.commonutil import getDateFormattedForDisplay
get_cart_query = "select \
crt.id as cart_id,\
crt.total_merchandise as total_merchandise,\
crt.total_shipping as total_shipping,\
crt.total_taxes as total_taxes,\
crt.total_discount as total_discount,\
crt.total_cart as total_cart, \
crt.status as cart_status,\
crt.delivery_date as delivery_date,\
crt.delivery_window as delivery_window,\
cust.id as customer_id,\
cust.customer_type as customer_type,\
pymt.id as  payment_id, \
pymt.payment_method as  payment_method, \
pymt.account_number as  account_number, \
pymt.account_name as  account_name, \
pymt.expiry_month as  expiry_month, \
pymt.expiry_year as  expiry_year, \
pymt.transaction_id as  transaction_id, \
pymt.transaction_status as  transaction_status, \
pymt.approved_amount as  approved_amount, \
itm.id as item_id,\
itm.product_price as item_product_price,\
itm.status as item_status,\
itm.delivery_date as item_delivery_date,\
itm.shipping_base_charge as item_shipping_base_charge,\
itm.shipping_up_charge as item_shipping_up_charge,\
itm.total_shipping as item_total_shipping,\
itm.shipping_tax as item_shipping_tax,\
itm.merchandise_tax as item_merchandise_tax,\
itm.total_tax as item_total_tax,\
itm.merchandise_discount as item_merchandise_discount,\
itm.shipping_discount as item_shipping_discount,\
itm.total_discount as item_total_discount,\
prd.id as product_id,\
prd.sku as product_sku,\
prd.name as product_name,\
prd.description as product_description,\
prd.retail_price as product_retail_price,\
prd.sale_price as product_sale_price,\
prd.main_image as product_image,\
prd.is_active as product_is_active,\
prd.is_sustainable as product_is_sustainable,\
prd.is_handmade as product_is_handmade,\
prd.display as product_display,\
vr.id as variant_id,\
vr.size as product_size,\
vr.quantity as product_quantity,\
vr.description as size_description,\
vr.variant_image as size_image,\
vr.is_default as default_size,\
baddr.id as billing_address_id,\
baddr.first_name as billing_first_name,\
baddr.last_name as billing_last_name,\
baddr.address1 as billing_address1,\
baddr.address2 as billing_address2,\
baddr.city as billing_city,\
baddr.state as billing_state,\
baddr.zip as billing_zip,\
baddr.country as billing_country,\
baddr.phone as billing_phone, \
baddr.email as billing_email, \
saddr.id as shipping_address_id,\
saddr.first_name as shipping_first_name,\
saddr.last_name as shipping_last_name,\
saddr.address1 as shipping_address1,\
saddr.address2 as shipping_address2,\
saddr.city as shipping_city,\
saddr.state as shipping_state,\
saddr.zip as shipping_zip,\
saddr.country as shipping_country, \
saddr.phone as shipping_phone, \
saddr.email as shipping_email \
FROM \
cart crt \
inner join customer cust on cust.id = crt.customer_id \
inner join payment pymt on pymt.cart_id = crt.id \
inner join item itm on itm.cart_id = crt.id \
inner join product prd on prd.id = itm.product_id \
left outer join variant vr on vr.id = itm.size_id \
left outer join address baddr on baddr.id = cust.billing_address_id \
left outer join address saddr on saddr.id = cust.shipping_address_id \
where crt.id =:cartId and crt.customer_id=:customerId and pymt.transaction_status='APPROVED' \
order by itm.created_at desc"

def get_cart(cartId):
   cart = {}
   curr_customer_id = session.get('customer_id')
   value={"cartId":cartId,"customerId":curr_customer_id} 
   sql = text(get_cart_query)
   result = db.session.execute(sql,value)
   for row in result:
        if row.cart_id in cart:
            cart_obj = cart.get(row.cart_id)
        else:    
         cart_obj = {}
        cart[row.cart_id]  = build_main_cart(cart_obj,row)  
   return cart

def build_main_cart(cart_obj,row):
    cart_obj['cart_id']= row.cart_id
    cart_obj['total_merchandise']= row.total_merchandise
    cart_obj['total_shipping']= row.total_shipping
    cart_obj['total_taxes']= row.total_taxes
    cart_obj['total_discount']= row.total_discount
    cart_obj['total_cart']= row.total_cart
    cart_obj['cart_status']= row.cart_status
    cart_obj['delivery_date'] = row.delivery_date
    cart_obj['formatted_delivery_date'] = getDateFormattedForDisplay(row.delivery_date)
    cart_obj['delivery_window'] = row.delivery_window
    cart_obj['customer']= build_customer(row,cart_obj)
    cart_obj['cart_items'] = build_cart_items(row,cart_obj)
    cart_obj['payments'] = build_payments(row,cart_obj)
    return cart_obj

def build_cart_items(row,cart_obj):
    if 'cart_items' in cart_obj:
        items_obj = cart_obj.get('cart_items')
    else:    
       items_obj = {}
    items_obj[row.item_id] = build_item_obj(row,items_obj)
    return items_obj 
def build_payments(row,cart_obj):
    if 'payments' in cart_obj:
        payments_obj = cart_obj.get('payments')
    else:    
       payments_obj = {}
    payments_obj[row.payment_id] = build_payment_obj(row,payments_obj)
    return payments_obj

def build_payment_obj(row,payments_obj):
    if row.payment_id in payments_obj:
        payment_obj = payments_obj.get(row.payment_id)
    else:    
       payment_obj = {}
    payment_obj['payment_id'] = row.payment_id
    payment_obj['payment_method']= row.payment_method
    payment_obj['account_number']= row.account_number
    payment_obj['account_name'] = row.account_name
    payment_obj['expiry_month']= row.expiry_month
    payment_obj['expiry_year'] = row.expiry_year
    payment_obj['transaction_id']= row.transaction_id
    payment_obj['transaction_status'] = row.transaction_status
    payment_obj['approved_amount']= row.approved_amount
    return payment_obj
     
def build_item_obj(row,items_obj):
    if row.item_id in items_obj:
        item_obj = items_obj.get(row.item_id)
    else:    
       item_obj = {}
    item_obj['item_id'] = row.item_id
    item_obj['item_product_price']= row.item_product_price
    item_obj['item_status'] = row.item_status
    item_obj['item_delivery_date']= row.item_delivery_date
    item_obj['item_shipping_base_charge'] = row.item_shipping_base_charge
    item_obj['item_shipping_up_charge']= row.item_shipping_up_charge
    item_obj['total_shipping'] = row.total_shipping
    item_obj['item_shipping_tax']= row.item_shipping_tax
    item_obj['item_merchandise_tax'] = row.item_merchandise_tax
    item_obj['item_total_tax']= row.item_total_tax
    item_obj['item_merchandise_discount'] = row.item_merchandise_discount
    item_obj['item_shipping_discount']= row.item_shipping_discount
    item_obj['item_total_discount'] = row.item_total_discount
    item_obj['product']= build_product(row,item_obj)
    return item_obj

def build_product(row,item_obj):
    if row.product_id in item_obj:
        product_obj = item_obj.get(row.product_id)
    else:    
       product_obj = {}
    product_obj[row.product_id] = build_product_from_row(row)
    return product_obj

def build_product_from_row(row):
    product = {}
    product['product_id'] = row.product_id
    product['product_sku'] = row.product_sku
    product['product_name'] = row.product_name
    product['product_description'] = row.product_description
    product['product_retail_price'] = row.product_retail_price
    product['product_sale_price'] = row.product_sale_price
    product['product_image'] = row.product_image
    product['product_is_active'] = row.product_is_active
    product['product_is_sustainable'] = row.product_is_sustainable
    product['product_is_active'] = row.product_is_active
    product['size'] = create_size_from_row(row)
    return product

def create_size_from_row(row):
   size={}
   size['size_id']=row.variant_id
   size['product_size'] = row.product_size
   size['product_quantity']= row.product_quantity
   size['size_description'] = row.size_description
   size['size_image']= row.size_image
   size['default_size']=row.default_size
   return size


def build_customer(row,cart_obj):
    if 'customer' in cart_obj:
        customer_obj = cart_obj.get('customer')
    else:    
       customer_obj = {}
    customer_obj['customer_id'] = row.customer_id
    customer_obj['customer_type'] = row.customer_type
    customer_obj['billing_address'] = build_billing_address(customer_obj,row)
    customer_obj['shipping_address'] = build_shipping_address(customer_obj,row)  
    return customer_obj

def build_billing_address(customer_obj, row):
    if 'billing_address' in customer_obj:
        billing_add_obj = customer_obj.get('billing_address')
    else:    
       billing_add_obj = {}
    if row.billing_address_id:
        billing_add_obj['billing_address_id'] = row.billing_address_id
        billing_add_obj['billing_first_name'] = row.billing_first_name
        billing_add_obj['billing_last_name']  = row.billing_last_name
        billing_add_obj['billing_address1'] = row.billing_address1
        billing_add_obj['billing_address2'] = row.billing_address2
        billing_add_obj['billing_city'] = row.billing_city
        billing_add_obj['billing_state'] = row.billing_state
        billing_add_obj['billing_zip'] = row.billing_zip
        billing_add_obj['billing_country'] = row.billing_country
        billing_add_obj['billing_phone'] = row.billing_phone
        billing_add_obj['billing_email'] = row.billing_email
        return billing_add_obj
    return None

def build_shipping_address(customer_obj, row):
    if 'shipping_address' in customer_obj:
        shipping_add_obj = customer_obj.get('shipping_address')
    else:    
       shipping_add_obj = {}
    if row.shipping_address_id:   
        shipping_add_obj['shipping_address_id'] = row.shipping_address_id
        shipping_add_obj['shipping_first_name'] = row.shipping_first_name
        shipping_add_obj['shipping_last_name']  = row.shipping_last_name
        shipping_add_obj['shipping_address1'] = row.shipping_address1
        shipping_add_obj['shipping_address2'] = row.shipping_address2
        shipping_add_obj['shipping_city'] = row.shipping_city
        shipping_add_obj['shipping_state'] = row.shipping_state
        shipping_add_obj['shipping_zip'] = row.shipping_zip
        shipping_add_obj['shipping_country'] = row.shipping_country
        shipping_add_obj['shipping_phone'] = row.shipping_phone
        shipping_add_obj['shipping_email'] = row.shipping_email
        return shipping_add_obj
    return None
