import datetime

from flask import session

from app.extension import db
from app.models import Cart, Customer


def get_current_pending_cart():
    curr_customer_id = session.get("customer_id")
    if curr_customer_id:
        cart = db.session.query(Cart).filter(Cart.customer_id == curr_customer_id, Cart.status == "PENDING")
    if cart or cart.count() == 1:
        return cart
    elif cart.count() > 1:
        cart.update({"status": "CANCELLED"})
        db.session.commit()
        return None
    return


def get_current_customer():
    customer_id = session.get("customer_id")
    customer = db.session.query(Customer).filter(Customer.id == customer_id)
    if customer and customer.count() == 1:
        return customer


def getUSStates():
    states = [
        ("AL", "Alabama"),
        ("AK", "Alaska"),
        ("AS", "American Samoa"),
        ("AZ", "Arizona"),
        ("AR", "Arkansas"),
        ("CA", "California"),
        ("CO", "Colorado"),
        ("CT", "Connecticut"),
        ("DE", "Delaware"),
        ("DC", "District of Columbia"),
        ("FL", "Florida"),
        ("GA", "Georgia"),
        ("GU", "Guam"),
        ("HI", "Hawaii"),
        ("ID", "Idaho"),
        ("IL", "Illinois"),
        ("IN", "Indiana"),
        ("IA", "Iowa"),
        ("KS", "Kansas"),
        ("KY", "Kentucky"),
        ("LA", "Louisiana"),
        ("ME", "Maine"),
        ("MD", "Maryland"),
        ("MA", "Massachusetts"),
        ("MI", "Michigan"),
        ("MN", "Minnesota"),
        ("MS", "Mississippi"),
        ("MO", "Missouri"),
        ("MT", "Montana"),
        ("NE", "Nebraska"),
        ("NV", "Nevada"),
        ("NH", "New Hampshire"),
        ("NJ", "New Jersey"),
        ("NM", "New Mexico"),
        ("NY", "New York"),
        ("NC", "North Carolina"),
        ("ND", "North Dakota"),
        ("MP", "Northern Mariana Islands"),
        ("OH", "Ohio"),
        ("OK", "Oklahoma"),
        ("OR", "Oregon"),
        ("PA", "Pennsylvania"),
        ("PR", "Puerto Rico"),
        ("RI", "Rhode Island"),
        ("SC", "South Carolina"),
        ("SD", "South Dakota"),
        ("TN", "Tennessee"),
        ("TX", "Texas"),
        ("UT", "Utah"),
        ("VT", "Vermont"),
        ("VI", "Virgin Islands"),
        ("VA", "Virginia"),
        ("WA", "Washington"),
        ("WV", "West Virginia"),
        ("WI", "Wisconsin"),
        ("WY", "Wyoming"),
    ]

    return states


def isNotEmpty(str):
    isempty = not (str and str.strip())
    return not isempty


def getCustomerFromCart(cart):
    cart_obj = getCartObj(cart)
    if cart_obj and "customer" in cart_obj:
        return cart_obj.get("customer")


def getCartObj(cart):
    if cart and len(cart) > 0:
        cart_obj = cart.get(next(iter(cart)))
        return cart_obj


def getShippingAddressFromCart(cart):
    customer = customer = getCustomerFromCart(cart)
    if customer and "shipping_address" in customer:
        ship_add = customer.get("shipping_address")
        return ship_add


def getBillingAddressFromCart(cart):
    customer = getCustomerFromCart(cart)
    if customer and "billing_address" in customer:
        bill_add = customer.get("billing_address")
        return bill_add


def getDeliveryDateFromCart(cart):
    cart_obj = getCartObj(cart)
    if cart_obj:
        del_date = cart_obj.get("delivery_date")
        return del_date


def getFormattedDeliveryDateFromCart(cart):
    cart_obj = getCartObj(cart)
    if cart_obj:
        del_date = cart_obj.get("formatted_delivery_date")
        return del_date


def getDeliveryWindowFromCart(cart):
    cart_obj = getCartObj(cart)
    if cart_obj:
        del_window = cart_obj.get("delivery_window")
        return del_window


def convertDate(dateStr, format):
    try:
        return datetime.datetime.strptime(dateStr, format)
    except:
        return dateStr


def getFormatedDate(dttm, format):
    try:
        formatted_date = dttm.strftime(format)
        return formatted_date
    except:
        return dttm


def check_billing_address(cart):
    isComplete = False
    bill_add = getBillingAddressFromCart(cart)
    if bill_add:
        isComplete = (
            isNotEmpty(bill_add.get("billing_first_name"))
            and isNotEmpty(bill_add.get("billing_last_name"))
            and isNotEmpty(bill_add.get("billing_address1"))
            and isNotEmpty(bill_add.get("billing_city"))
            and isNotEmpty(bill_add.get("billing_state"))
            and isNotEmpty(bill_add.get("billing_zip"))
            and isNotEmpty(bill_add.get("billing_country"))
            and isNotEmpty(bill_add.get("billing_phone"))
            and isNotEmpty(bill_add.get("billing_email"))
        )
    return isComplete


def check_shipping_address(cart):
    isComplete = False
    ship_add = getShippingAddressFromCart(cart)
    if ship_add:
        isComplete = (
            isNotEmpty(ship_add.get("shipping_first_name"))
            and isNotEmpty(ship_add.get("shipping_last_name"))
            and isNotEmpty(ship_add.get("shipping_address1"))
            and isNotEmpty(ship_add.get("shipping_city"))
            and isNotEmpty(ship_add.get("shipping_state"))
            and isNotEmpty(ship_add.get("shipping_zip"))
            and isNotEmpty(ship_add.get("shipping_country"))
            and isNotEmpty(ship_add.get("shipping_phone"))
            and isNotEmpty(ship_add.get("shipping_email"))
        )
    return isComplete


def check_delivery_date(cart):
    isComplete = False
    lead_time_date = datetime.date.today() + datetime.timedelta(3)
    del_date = getDeliveryDateFromCart(cart)
    if del_date:
        cd = convertDate(del_date, "%Y-%m-%d %H:%M:%S.%f")
        isComplete = True if cd and cd.date() > lead_time_date else False
    return isComplete


def getDateFormattedForDisplay(delivery_date):
    if delivery_date:
        formatted_date = getFormatedDate(convertDate(delivery_date, "%Y-%m-%d %H:%M:%S.%f"), "%a, %d  %b  %Y")
        return formatted_date
