s_query = "select  \
    h.hero_image as hero_banner, \
    c.name as carousel_name,\
    c.header as carousel_header,\
    c.text as carousel_text,\
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
    p1.display as collection_product_display,\
    c2.id as featured_category_id,\
    c2.code as featured_category_code,\
    c2.name as featured_category_name,\
    c2.is_active as featured_category_status,\
    p2.id as featured_product_id,\
    p2.sku as featured_product_sku,\
    p2.name as featured_product_name,\
    p2.description as featured_product_description,\
    p2.retail_price as featured_product_retail_price,\
    p2.sale_price as featured_product_sale_price,\
    p2.main_image as featured_product_main_image,\
    p2.alt1_image as featured_product_alt1_image,\
    p2.alt2_image as featured_product_alt2_image,\
    p2.alt3_image as featured_product_alt3_image,\
    p2.is_active as featured_product_is_active,\
    p2.is_sustainable as featured_product_is_sustainable,\
    p2.is_handmade as featured_product_is_handmade,\
    p2.display as featured_product_display\
    from home_content h \
    left outer join home_carousel_rel hcr on hcr.home_content_id = h.id\
    left outer join carousel c on c.id = hcr.carousel_id\
    left outer join collection m on m.id = h.collection_id and m.is_active=true\
    left outer join collection_category_rel mcr on mcr.collection_id = m.id\
    left outer join category c1 on c1.id = mcr.category_id\
    left outer join category_product_rel cpr1 on cpr1.category_id = c1.id\
    left outer join product p1 on p1.id = cpr1.product_id\
    left outer join category c2 on c2.id = h.category_id\
    left outer join category_product_rel cpr2 on cpr2.category_id = c2.id\
    left outer join product p2 on p2.id = cpr2.product_id\
    where h.is_active=true;"


def create_featured_product_from_row(row):
    prod_obj = {}
    prod_obj["product_id"] = row.featured_product_id
    prod_obj["product_sku"] = row.featured_product_sku
    prod_obj["product_name"] = row.featured_product_name
    prod_obj["product_description"] = row.featured_product_description
    prod_obj["product_retail_price"] = row.featured_product_retail_price
    prod_obj["product_sale_price"] = row.featured_product_sale_price
    prod_obj["product_main_image"] = row.featured_product_main_image
    prod_obj["product_alt1_image"] = row.featured_product_alt1_image
    prod_obj["product_alt2_image"] = row.featured_product_alt2_image
    prod_obj["product_alt3_image"] = row.featured_product_alt3_image
    prod_obj["product_is_active"] = row.featured_product_is_active
    prod_obj["product_is_sustainable"] = row.featured_product_is_sustainable
    prod_obj["product_is_handmade"] = row.featured_product_is_handmade
    prod_obj["product_display"] = row.featured_product_display

    return prod_obj


def build_featured_category_products(row, category_dic):
    if "products" in category_dic:
        products_dic = category_dic.get("products")
    else:
        products_dic = {}

    if row.featured_product_is_active:
        products_dic[row.featured_product_id] = create_featured_product_from_row(row)
    return products_dic


def create_featured_category_from_row(row, categories_dic):
    if row.featured_category_id in categories_dic:
        category_obj = categories_dic.get(row.featured_category_id)
    else:
        category_obj = {}
    category_obj["category_id"] = row.featured_category_id
    category_obj["category_code"] = row.featured_category_code
    category_obj["category_name"] = row.featured_category_name
    category_obj["products"] = build_featured_category_products(row, category_obj)
    return category_obj


def build_featured_categories(row, featured_dic):
    if "categories" in featured_dic:
        categories_dic = featured_dic.get("categories")
    else:
        categories_dic = {}
    if row.featured_category_status:
        categories_dic[row.featured_category_id] = create_featured_category_from_row(row, categories_dic)
    return categories_dic


def build_featured_category(row, home):
    if "featured" in home:
        featured_dic = home.get("featured")
    else:
        featured_dic = {}
    featured_dic["categories"] = build_featured_categories(row, featured_dic)

    return featured_dic


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


def create_carousel(row, carousel_dic):
    if row.carousel_name in carousel_dic:
        carousel_obj = carousel_dic.get(row.carousel_name)
    else:
        carousel_obj = {}
    carousel_obj["header"] = row.carousel_header
    carousel_obj["text"] = row.carousel_text
    return carousel_obj


def build_carousel(row, home):
    if "carousel" in home:
        carousel_dic = home.get("carousel")
    else:
        carousel_dic = {}
    carousel_dic[row.carousel_name] = create_carousel(row, carousel_dic)
    return carousel_dic


def build_collection_category(row, home):
    if "collection" in home:
        collection_dic = home.get("collection")
    else:
        collection_dic = {}
    collection_dic["categories"] = build_categories(row, collection_dic)

    return collection_dic


def build_home_page(result):
    home = {}
    for row in result:
        # set hero image for home page
        home["heroImage"] = row.hero_banner
        home["carousel"] = build_carousel(row, home)
        home["collection"] = build_collection_category(row, home)
        home["featured"] = build_featured_category(row, home)

    return home
