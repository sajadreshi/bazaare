from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,SelectField,HiddenField
from wtforms.validators import DataRequired, Email,ValidationError,Length
from app.checkout.commonutil import getUSStates,getShippingAddressFromCart,getBillingAddressFromCart,getFormattedDeliveryDateFromCart,getDeliveryWindowFromCart
from app.checkout.deliveryDateHelper import fetchDeliveryDays


class ShippingForm(FlaskForm):
    first_name = StringField('First Name',validators=[Length(max=100),DataRequired()], render_kw={"placeholder": "First Name"})
    last_name = StringField('Last Name',validators=[Length(max=100),DataRequired()], render_kw={"placeholder": "Last Name"})
    address1 = StringField('Address Line1',validators=[DataRequired()], render_kw={"placeholder": "Address Line 1"})
    address2 = StringField('Address Line2', render_kw={"placeholder": "Address Line 2 (Optional)"})
    city = StringField('City',validators=[DataRequired()], render_kw={"placeholder": "City"})
    state = SelectField('State',validators=[DataRequired()], choices=getUSStates())
    zip =  StringField('Zip',validators=[Length(max=10),DataRequired()], render_kw={"placeholder": "Zip"})
    email = StringField('Email',validators=[DataRequired(),Email()], render_kw={"placeholder": "Email"})
    phone = StringField('Phone',validators=[Length(max=14),DataRequired()], render_kw={"placeholder": "Phone"})
    form_id = HiddenField("FormId",default='shipping_form')
    submit = SubmitField('Continue')

class BillingForm(FlaskForm):
    first_name = StringField('First Name',validators=[Length(max=100),DataRequired()], render_kw={"placeholder": "First Name"})
    last_name = StringField('Last Name',validators=[Length(max=100),DataRequired()], render_kw={"placeholder": "Last Name"})
    address1 = StringField('Address Line1',validators=[DataRequired()], render_kw={"placeholder": "Address Line 1"})
    address2 = StringField('Address Line2', render_kw={"placeholder": "Address Line 2 (Optional)"})
    city = StringField('City',validators=[DataRequired()], render_kw={"placeholder": "City"})
    state = SelectField('State', validators=[DataRequired()],choices=getUSStates())
    zip =  StringField('Zip',validators=[Length(max=10),DataRequired()], render_kw={"placeholder": "Zip"})
    email = StringField('Email',validators=[DataRequired(),Email()], render_kw={"placeholder": "Email"})
    phone = StringField('Phone',validators=[Length(max=14),DataRequired()], render_kw={"placeholder": "Phone"})
    form_id = HiddenField("FormId",default='billing_form')
    submit = SubmitField('Continue')

class DeliveryDateForm(FlaskForm):
    delivery_date = SelectField('Delivery Date',validators=[DataRequired()],choices=[],validate_choice=False)
    delivery_window = SelectField('Delivery Window',validators=[DataRequired()],choices=[],validate_choice=False)
    form_id = HiddenField("FormId",default='delivery_form')
    submit = SubmitField('Continue')

class PlaceOrderForm(FlaskForm):
    payment_method = SelectField('Delivery Date',validators=[DataRequired()],choices=[('COD','Cash On Delivery')],validate_choice=False)
    form_id = HiddenField("FormId",default='place_order_form')
    submit = SubmitField('Place Order')

def prepopulateShippingForm(cart, ship_frm):
    ship_address = getShippingAddressFromCart(cart)
    if ship_address:
       ship_frm.first_name.data = ship_address.get('shipping_first_name')
       ship_frm.last_name.data = ship_address.get('shipping_last_name')
       ship_frm.address1.data = ship_address.get('shipping_address1')
       ship_frm.address2.data = ship_address.get('shipping_address2')
       ship_frm.city.data = ship_address.get('shipping_city')
       ship_frm.state.data = ship_address.get('shipping_state')
       ship_frm.zip.data = ship_address.get('shipping_zip')
       ship_frm.email.data = ship_address.get('shipping_email')
       ship_frm.phone.data = ship_address.get('shipping_phone')
    return ship_frm

def prepopulateBillingForm(cart, bill_frm):
    bill_address = getBillingAddressFromCart(cart)
    if bill_address:
       bill_frm.first_name.data = bill_address.get('billing_first_name')
       bill_frm.last_name.data = bill_address.get('billing_last_name')
       bill_frm.address1.data = bill_address.get('billing_address1')
       bill_frm.address2.data = bill_address.get('billing_address2')
       bill_frm.city.data = bill_address.get('billing_city')
       bill_frm.state.data = bill_address.get('billing_state')
       bill_frm.zip.data = bill_address.get('billing_zip')
       bill_frm.email.data = bill_address.get('billing_email')
       bill_frm.phone.data = bill_address.get('billing_phone')
    return bill_frm

def prepopulateDeliveryForm(cur_cart,del_frm):
    curr_delivey_date = getFormattedDeliveryDateFromCart(cur_cart)
    curr_delivery_window = getDeliveryWindowFromCart(cur_cart)
    if curr_delivey_date:
        del_frm.delivery_date.data = curr_delivey_date
    if curr_delivery_window:
        del_frm.delivery_window.data = curr_delivery_window
    del_frm.delivery_date.choices = fetchDeliveryDays()
    del_frm.delivery_window.choices = [("Morning","Morning"),("Afternoon","Afternoon"),("Evening","Evening")]
    return del_frm