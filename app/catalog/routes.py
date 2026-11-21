from app.catalog import catalog
from app.catalog.collectionbuilder import m_query,build_collection
from app.catalog.productbuilder import p_query,build_product,build_crossells
from app.catalog.addtocarthelper import add_item_to_cart,get_size
from app.checkout.getcarthelper import get_current_cart
from flask import render_template,redirect,flash,url_for,request
import pprint



@catalog.route("/collection",methods=["GET"])
def collection():  
    collection = build_collection()
    pprint.pprint(collection)       
    return render_template("catalog/collection.html", collection=collection)


@catalog.route("/product/<productId>",methods=["GET","POST"])
def product(productId):
    cur_cart = {}
    if request.method == 'POST':
       pid = request.form.get('pid','')
       size_id = request.form.get('size','')
       current_product = build_product(pid)
       product_size = get_size(current_product,size_id)
       #if no sizes are available, then throw out of stock message
       if(product_size is None ):
          flash('Product is currently out of stock')
          return redirect(url_for('catalog.product',productId=productId))
       
       add_item_to_cart(current_product,product_size)
       cur_cart = get_current_cart()
    product = build_product(productId)
    xsells = build_crossells(productId)           
    return render_template("catalog/product.html", product=product,xsells=xsells,cart=cur_cart)

