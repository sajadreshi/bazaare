from sqlalchemy import text

from app.extension import db

m_query = "select \
c1.id as collection_category_id,\
c1.code as collection_category_code,\
c1.name as collection_category_name,\
c1.is_active as collection_category_status,\
p1.id as collection_product_id,\
p1.sku as collection_product_sku,\
p1.name as collection_product_name,\
p1.description as collection_product_description,\
p1.retail_price as collection_product_retail_price,\
p1.sale_price as collection_product_sale_price,\
p1.main_image as collection_product_main_image,\
p1.alt1_image as collection_product_alt1_image,\
p1.alt2_image as collection_product_alt2_image,\
p1.alt3_image as collection_product_alt3_image,\
p1.is_active as collection_product_is_active,\
p1.is_sustainable as collection_product_is_sustainable,\
p1.is_handmade as collection_product_is_handmade,\
p1.display as collection_product_display \
from collection m \
  left outer join collection_category_rel mcr on mcr.collection_id = m.id\
  left outer join category c1 on c1.id = mcr.category_id\
  left outer join category_product_rel cpr1 on cpr1.category_id = c1.id\
  left outer join product p1 on p1.id = cpr1.product_id\
  where m.is_active=true;"


def create_product_from_row(row):
    prod_obj = {}
    prod_obj["product_id"] = row.collection_product_id
    prod_obj["product_sku"] = row.collection_product_sku
    prod_obj["product_name"] = row.collection_product_name
    prod_obj["product_description"] = row.collection_product_description
    prod_obj["product_retail_price"] = row.collection_product_retail_price
    prod_obj["product_sale_price"] = row.collection_product_sale_price
    prod_obj["product_main_image"] = row.collection_product_main_image
    prod_obj["product_alt1_image"] = row.collection_product_alt1_image
    prod_obj["product_alt2_image"] = row.collection_product_alt2_image
    prod_obj["product_alt3_image"] = row.collection_product_alt3_image
    prod_obj["product_is_active"] = row.collection_product_is_active
    prod_obj["product_is_sustainable"] = row.collection_product_is_sustainable
    prod_obj["product_is_handmade"] = row.collection_product_is_handmade
    prod_obj["product_display"] = row.collection_product_display

    return prod_obj


def build_category_products(row, category_dic):
    if "products" in category_dic:
        products_dic = category_dic.get("products")
    else:
        products_dic = {}

    if row.collection_product_is_active:
        products_dic[row.collection_product_id] = create_product_from_row(row)
    return products_dic


def create_category_from_row(row, categories_dic):
    if row.collection_category_id in categories_dic:
        category_obj = categories_dic.get(row.collection_category_id)
    else:
        category_obj = {}
    category_obj["category_id"] = row.collection_category_id
    category_obj["category_code"] = row.collection_category_code
    category_obj["category_name"] = row.collection_category_name
    category_obj["products"] = build_category_products(row, category_obj)
    return category_obj


def build_categories(row, collection_dic):
    if "categories" in collection_dic:
        categories_dic = collection_dic.get("categories")
    else:
        categories_dic = {}
    if row.collection_category_status:
        categories_dic[row.collection_category_id] = create_category_from_row(row, categories_dic)
    return categories_dic


def build_collection():
    collection = {}
    sql = text(m_query)
    result = db.session.execute(sql)
    for row in result:
        collection["categories"] = build_categories(row, collection)
    return collection
