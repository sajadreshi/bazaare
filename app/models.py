import jwt
from time import time
from .extension import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app as app



class User(UserMixin,db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100),nullable=False)
    last_name = db.Column(db.String(100),index=True,nullable=False)
    email = db.Column(db.String(100),index=True, unique=True,nullable=False)
    password = db.Column(db.String(300),nullable=False)
    is_admin = db.Column(db.Boolean,nullable=False,default=False)
    marketting_email = db.Column(db.Boolean,nullable=True, default=False)
    transactional_email = db.Column(db.Boolean,nullable=True, default=True)
    marketting_sms = db.Column(db.Boolean,nullable=True, default=False)
    transactional_sms = db.Column(db.Boolean,nullable=True, default=True)
    cell_number = db.Column(db.String(20))
    roles = db.relationship('Role', secondary='user_roles')
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)

    def set_password(self, password):
        self.password= generate_password_hash(password)
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return db.session.get(User, id)
    
    def check_password(self, password):
        h = check_password_hash(self.password, password)   
        return h 

    def is_active(self):
        return True

    def is_authenticated(self):
        return self.is_authenticated

    def is_anonymous(self):
        return False

    def is_admin(self):
        return self.is_admin
    
    def get_id(self):
        return self.id

    def __repr__(self):
        return f"<User {self.email}>"
    
class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return self.name
    def __unicode__(self):
        return self.name

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))   
    

class Product(db.Model):
    __tablename__ = 'product'
    id=db.Column(db.Integer,primary_key=True)
    sku=db.Column(db.String(64),index=True,unique=True,nullable=False)
    name=db.Column(db.String(64),index=True,nullable=False)
    description=db.Column(db.String(300))
    retail_price=db.Column(db.Float,nullable=False)
    sale_price=db.Column(db.Float,nullable=False)
    main_image=db.Column(db.Unicode(128))
    alt1_image=db.Column(db.Unicode(128))
    alt2_image=db.Column(db.Unicode(128))
    alt3_image=db.Column(db.Unicode(128))
    is_handmade=db.Column(db.Boolean, default=False)
    is_sustainable=db.Column(db.Boolean, default=False)
    material=db.Column(db.String(100))
    is_active=db.Column(db.Boolean, default=False)
    display=db.Column(db.Boolean, default=False)
    unit_quantity = db.Column(db.Integer)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    variant_id=db.Column(db.Integer, db.ForeignKey('variant.id'))
    categories = db.relationship('Category', secondary="category_product_rel", 
                                 backref=db.backref('product', lazy='dynamic'))
    
    
    def __repr__(self):
        return self.name
    def __unicode__(self):
        return self.name

class Variant(db.Model):
    __tablename__ = 'variant'
    id=db.Column(db.Integer,primary_key=True)
    size = db.Column(db.String(30),nullable=False)
    quantity =  db.Column(db.Float,nullable=False)
    weight=db.Column(db.Float)
    is_default = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(300))
    variant_image=db.Column(db.Unicode(128))
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    products = db.relationship('Product', secondary="variant_product_rel", 
                                 backref=db.backref('variant', lazy='dynamic'))

    def __repr__(self):
        return self.size

class VariantProduct(db.Model):
    __tablename__ = 'variant_product_rel'
    id=db.Column(db.Integer, primary_key=True)
    variant_id=db.Column(db.Integer, db.ForeignKey('variant.id'),nullable=False)
    product_id=db.Column(db.Integer, db.ForeignKey('product.id'),nullable=False)
    association_type = db.Column(db.String(30),nullable=True)

class ProductAssociation(db.Model):

    __tablename__ = 'product_association'
    id=db.Column(db.Integer, primary_key=True)
    source_product_id=db.Column(db.Integer, db.ForeignKey('product.id'),nullable=False)
    target_product_id=db.Column(db.Integer, db.ForeignKey('product.id'),nullable=False)
    is_active=db.Column(db.Boolean, default=False)
    association_type = db.Column(db.String(30),nullable=False)
    source_product = db.relationship('Product',foreign_keys=[source_product_id])
    target_product = db.relationship('Product',foreign_keys=[target_product_id])


class Attribute(db.Model):
    __tablename__ = 'attribute'
    id=db.Column(db.Integer, primary_key=True)
    attribute_name = db.Column(db.String(64),index=True,unique=True,nullable=False) 
    attribute_value = db.Column(db.String(300))
    

    def __repr__(self):
        return self.attribute_name
    
    def __unicode__(self):
        return self.attribute_name
    
class ProductAttribute(db.Model):
    __tablename__ = 'product_attribute_rel'
    id=db.Column(db.Integer, primary_key=True)
    product_id=db.Column(db.Integer, db.ForeignKey('product.id',ondelete='CASCADE'),nullable=False)
    attribute_id=db.Column(db.Integer, db.ForeignKey('attribute.id',ondelete='CASCADE'),nullable=False)
    product = db.relationship('Product', backref='product')
    attribute = db.relationship('Attribute', backref='attribute')

    
class Category(db.Model):
    __tablename__ = 'category'
    id=db.Column(db.Integer, primary_key=True)
    code=db.Column(db.String(64),index=True,unique=True,nullable=False)
    name=db.Column(db.String(64),index=True,nullable=False)
    description=db.Column(db.String(300))
    is_active=db.Column(db.Boolean, default=False)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    product_id=db.Column(db.Integer, db.ForeignKey('product.id'))
    collection = db.relationship('Collection', secondary="collection_category_rel", 
                                 backref=db.backref('category', lazy='dynamic'))
    home = db.relationship('HomePageContent', backref=db.backref('category',uselist=False))
    def __repr__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    
    
class ProductCategory(db.Model):
    __tablename__ = 'category_product_rel'
    id=db.Column(db.Integer, primary_key=True)
    product_id=db.Column(db.Integer, db.ForeignKey('product.id',ondelete='CASCADE'),nullable=False)
    category_id=db.Column(db.Integer, db.ForeignKey('category.id',ondelete='CASCADE'),nullable=False)   

class Collection(db.Model):
    __tablename__ = 'collection'
    id=db.Column(db.Integer, primary_key=True)   
    name=db.Column(db.String(64),index=True,nullable=False)
    description=db.Column(db.String(300))
    is_active=db.Column(db.Boolean, default=False)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    category_id=db.Column(db.Integer, db.ForeignKey('category.id'))
    home = db.relationship('HomePageContent', backref=db.backref('collection',uselist=False))
    
    
    def __repr__(self):
        return self.name
    
    def __unicode__(self):
        return self.name

class CollectionCategory(db.Model):

    __tablename__ = 'collection_category_rel'
    id=db.Column(db.Integer, primary_key=True)
    collection_id=db.Column(db.Integer, db.ForeignKey('collection.id',ondelete='CASCADE'),nullable=False)
    category_id=db.Column(db.Integer, db.ForeignKey('category.id',ondelete='CASCADE'),nullable=False)
    

class Carousal(db.Model):
    __tablename__ = 'carousal'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(64),nullable=False)
    header=db.Column(db.String(500),nullable=False)
    text = db.Column(db.Text,nullable=False)
    home = db.relationship('HomePageContent', secondary="home_carousal_rel", 
                                 backref=db.backref('carousal', lazy='dynamic'))
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    

    def __repr__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
class HomePageContent(db.Model):
     __tablename__ = 'home_content'
     id=db.Column(db.Integer,primary_key=True)
     hero_image=db.Column(db.Unicode(128))
     is_active=db.Column(db.Boolean, default=False)
     carousal_id=db.Column(db.Integer, db.ForeignKey('carousal.id'))
     category_id=db.Column(db.Integer, db.ForeignKey('category.id'))
     collection_id=db.Column(db.Integer, db.ForeignKey('collection.id'))
     updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
     created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)

     def __repr__(self):
        return self.hero_image

     
class HomeCarousal(db.Model):
    __tablename__ = 'home_carousal_rel'
    id=db.Column(db.Integer, primary_key=True)
    home_content_id=db.Column(db.Integer, db.ForeignKey('home_content.id',ondelete='CASCADE'),nullable=False)
    carousal_id=db.Column(db.Integer, db.ForeignKey('carousal.id',ondelete='CASCADE'),nullable=False)

class Cart(db.Model):
    __tablename__ = 'cart'
    id=db.Column(db.Integer, primary_key=True)
    total_merchandise=db.Column(db.Float,default=0.00)
    total_shipping=db.Column(db.Float,default=0.00)
    total_taxes=db.Column(db.Float,default=0.00)
    total_discount=db.Column(db.Float,default=0.00)
    total_cart=db.Column(db.Float,default=0.00)
    status=db.Column(db.String(64),index=True,default='PENDING',nullable=False)
    delivery_date=db.Column(db.DateTime,index=True)
    delivery_window=db.Column(db.String(64))
    customer_id=db.Column(db.BigInteger,db.ForeignKey('customer.id'), index=True)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)

class Item(db.Model):
    __tablename__ = 'item'
    id=db.Column(db.Integer, primary_key=True)
    cart_id=db.Column(db.Integer, db.ForeignKey('cart.id',ondelete='CASCADE'),nullable=False)
    product_id=db.Column(db.Integer, db.ForeignKey('product.id'))
    size_id=db.Column(db.Integer, db.ForeignKey('variant.id'))
    product_sku=db.Column(db.String(64),nullable=False)
    product_name=db.Column(db.String(300))
    product_price=db.Column(db.Float,default=0.00)
    status=db.Column(db.String(64),default='PENDING',nullable=False)
    delivery_date=db.Column(db.DateTime,index=True)
    shipping_base_charge=db.Column(db.Float,default=0.00)
    shipping_up_charge=db.Column(db.Float,default=0.00)
    merchandise_tax=db.Column(db.Float,default=0.00)
    shipping_tax=db.Column(db.Float,default=0.00)
    merchandise_discount= db.Column(db.Float,default=0.00)
    shipping_discount= db.Column(db.Float,default=0.00)
    total_shipping= db.Column(db.Float,default=0.00)
    total_tax =  db.Column(db.Float,default=0.00)
    total_discount =  db.Column(db.Float,default=0.00)
    total_item= db.Column(db.Float,default=0.00)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)

class ItemArr(db.Model):
    __tablename__ = 'item_attr'
    id=db.Column(db.Integer, primary_key=True)
    attr_name = db.Column(db.String(64),index=True,unique=True,nullable=False) 
    attr_value = db.Column(db.String(300))

class ItemAttrRel(db.Model):
    __tablename__ = 'item_attr_rel'
    id=db.Column(db.Integer, primary_key=True)
    item_id=db.Column(db.Integer, db.ForeignKey('item.id',ondelete='CASCADE'),nullable=False)
    attribute_id=db.Column(db.Integer, db.ForeignKey('item_attr.id',ondelete='CASCADE'),nullable=False)
    

class Customer(db.Model):
    __tablename__ = 'customer'
    id=db.Column(db.BigInteger, primary_key=True)
    customer_type=db.Column(db.String(60),default='GUEST')
    user_id=db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE'))
    shipping_address_id=db.Column(db.Integer, db.ForeignKey('address.id'))
    billing_address_id=db.Column(db.Integer, db.ForeignKey('address.id'))
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)

class Address(db.Model):
    __tablename__ = 'address'
    id=db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(200),nullable=False)
    last_name = db.Column(db.String(200),nullable=False)
    address1 = db.Column(db.String(200),nullable=False)
    address2 = db.Column(db.String(200))
    city=db.Column(db.String(100),nullable=False)
    state=db.Column(db.String(100),nullable=False)
    zip=db.Column(db.String(20),nullable=False)
    country=db.Column(db.String(20),default='US')
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    verifiedAddress=db.Column(db.Boolean,default=False)

class Holiday(db.Model):
    __tablename__ = 'holiday'
    id=db.Column(db.Integer, primary_key=True)
    holiday_date=db.Column(db.DateTime,index=True)

class Payment(db.Model):
    __tablename__ = 'payment'
    id=db.Column(db.Integer, primary_key=True)
    payment_method = db.Column(db.String(200),nullable=False)
    cart_id=db.Column(db.Integer, db.ForeignKey('cart.id'))
    account_number = db.Column(db.String(500))
    account_name = db.Column(db.String(500))
    expiry_month = db.Column(db.Integer)
    expiry_year = db.Column(db.Integer)
    transaction_id = db.Column(db.String(500))
    transaction_status = db.Column(db.String(500))
    auth_code = db.Column(db.String(500))
    requested_amount= db.Column(db.Float,default=0.00)
    approved_amount= db.Column(db.Float,default=0.00)
    updated_at=db.Column(db.DateTime,index=True,default=datetime.utcnow)
    created_at=db.Column(db.DateTime, index=True,default=datetime.utcnow)








