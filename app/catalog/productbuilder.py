from sqlalchemy import text
from app.extension import db

p_query = "SELECT \
        p.id as product_id,\
        p.sku as product_sku,\
        p.name as product_name,\
        p.description as product_description,\
        p.material as product_material,\
        p.retail_price as product_list_price,\
        p.sale_price as product_sale_price,\
        p.main_image as product_image,\
        p.alt1_image as product_image1,\
        p.alt2_image as product_image2,\
        p.alt3_image as product_image3,\
        p.is_handmade as is_product_handmade,\
        p.is_sustainable as is_product_sustainable,\
        p.is_active as is_product_active,\
        v.id as variant_id,\
        v.size as product_size,\
        v.quantity as product_quantity,\
        v.description as size_description,\
        v.variant_image as size_image,\
        v.is_default as default_size,\
        attr.id as attribute_id,\
        attr.attribute_name as attribute_name,\
        attr.attribute_value as attribute_value \
        from product p\
        left outer join variant_product_rel vpr on vpr.product_id = p.id\
        left outer join variant v on v.id = vpr.variant_id\
        left outer join product_attribute_rel patr on patr.product_id = p.id\
        left outer join attribute attr on attr.id = patr.attribute_id\
        where p.id=:productId and p.is_active=true;"

x_sell_query = "SELECT\
        p.id as product_id,\
        p.sku as product_sku,\
        p.name as product_name,\
        p.description as product_description,\
        p.material as product_material,\
        p.retail_price as product_list_price,\
        p.sale_price as product_sale_price,\
        p.main_image as product_image,\
        p.alt1_image as product_image1,\
        p.alt2_image as product_image2,\
        p.alt3_image as product_image3,\
        p.is_handmade as is_product_handmade,\
        p.is_sustainable as is_product_sustainable,\
        p.is_active as is_product_active \
        from product p \
        inner join product_association passoc on passoc.target_product_id = p.id\
        where passoc.source_product_id=:productId and passoc.association_type='XSELL' and passoc.is_active=true;"

def build_attribute_from_row(row):
   attribute = {}
   attribute['attribute_name'] = row.attribute_name
   attribute['attribute_value'] = row.attribute_value
   return attribute

def build_atttributes(row, product_dic):
    if 'attributes' in product_dic:
      attribute_dic = product_dic.get('attributes')
    else:
      attribute_dic = {}
    attribute_dic[row.attribute_id] = build_attribute_from_row(row)

    return attribute_dic

def create_size_from_row(row):
   size={}
   size['size_id']=row.variant_id
   size['product_size'] = row.product_size
   size['product_quantity']= row.product_quantity
   size['size_description'] = row.size_description
   size['size_image']= row.size_image
   size['default_size']=row.default_size
   return size


def build_size(row, product_dic):
    if 'sizes' in product_dic:
      size_dic = product_dic.get('sizes')
    else:
      size_dic = {}
    if(row.variant_id):  
      size_dic[row.variant_id] = create_size_from_row(row) 
    return size_dic   

def build_product(productId):
    product={}
    value={'productId': productId}
    sql = text(p_query)
    result = db.session.execute(sql,value)
    for row in result:
        product['product_id'] = row.product_id
        product['product_sku'] = row.product_sku
        product['product_name'] = row.product_name
        product['product_description'] = row.product_description
        product['product_material'] = row.product_material
        product['product_list_price'] = row.product_list_price
        product['product_sale_price'] = row.product_sale_price
        product['product_image'] = row.product_image
        product['product_image1'] = row.product_image1
        product['product_image2'] = row.product_image2
        product['product_image3'] = row.product_image3
        product['is_product_handmade'] = row.is_product_handmade
        product['is_product_sustainable'] = row.is_product_sustainable
        product['is_product_active'] = row.is_product_active
        product['sizes'] = build_size(row,product) 
        product['attributes'] = build_atttributes(row,product)          
    return product 

def build_xsell_product(row,xsell_dic):
    if row.product_id in xsell_dic:
      product_dic = xsell_dic.get(row.product_id)
    else:
      product_dic = {}
    product_dic['prouduct_id'] = row.product_id
    product_dic['product_sku'] = row.product_sku
    product_dic['product_name'] = row.product_name
    product_dic['product_description'] = row.product_description
    product_dic['product_list_price'] = row.product_list_price
    product_dic['product_sale_price'] = row.product_sale_price
    product_dic['product_image'] = row.product_image
    product_dic['product_image1'] = row.product_image1
    product_dic['product_image2'] = row.product_image2
    product_dic['product_image3'] = row.product_image3
    product_dic['is_product_handmade'] = row.is_product_handmade
    product_dic['is_product_sustainable'] = row.is_product_sustainable
    product_dic['is_product_active'] = row.is_product_active  
    return product_dic

def build_crossells(productId):
    xsells={}
    value={'productId': productId}
    sql = text(x_sell_query)
    result = db.session.execute(sql,value)
    for row in result:
      xsells[row.product_id]=build_xsell_product(row,xsells)
    return xsells 

