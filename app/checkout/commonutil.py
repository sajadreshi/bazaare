import datetime
import logging

from flask import session

from app.extension import db
from app.models import Cart, Customer

log = logging.getLogger(__name__)

# Days between ordering and the earliest delivery date we offer.
DELIVERY_LEAD_DAYS = 3


def get_current_pending_cart():
    """Query for the current customer's single PENDING cart, or None.

    Callers use ``.first()`` / ``.update()`` on the returned query.
    """
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    cart = db.session.query(Cart).filter(Cart.customer_id == customer_id, Cart.status == "PENDING")
    count = cart.count()
    if count == 1:
        return cart
    if count > 1:
        log.warning("Customer %s had %s pending carts; cancelling them", customer_id, count)
        cart.update({"status": "CANCELLED"})
        db.session.commit()
    return None


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
    """Parse a date string; values that are already datetimes (Postgres) pass through."""
    if not isinstance(dateStr, str):
        return dateStr
    try:
        return datetime.datetime.strptime(dateStr, format)
    except ValueError:
        return dateStr


def getFormatedDate(dttm, format):
    if not hasattr(dttm, "strftime"):
        return dttm
    return dttm.strftime(format)


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
    earliest = datetime.date.today() + datetime.timedelta(DELIVERY_LEAD_DAYS)
    del_date = getDeliveryDateFromCart(cart)
    if del_date:
        cd = convertDate(del_date, "%Y-%m-%d %H:%M:%S.%f")
        # Same rule as fetchDeliveryDays(): the earliest date offered is valid.
        isComplete = hasattr(cd, "date") and cd.date() >= earliest
    return isComplete


def getDateFormattedForDisplay(delivery_date):
    if delivery_date:
        formatted_date = getFormatedDate(convertDate(delivery_date, "%Y-%m-%d %H:%M:%S.%f"), "%a, %d  %b  %Y")
        return formatted_date
