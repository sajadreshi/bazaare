from app import db
from app.models import Address
from app.checkout.commonutil import get_current_pending_cart,get_current_customer

def save_shipping_address(shipping_form):
    current_cart = get_current_pending_cart()
    if current_cart:
        ship_address = persist_address(shipping_form)
        customer = get_current_customer()
        if customer and ship_address:
            customer.update({'shipping_address_id': ship_address.id})
            customer_data= customer.first()
            if customer_data.billing_address_id is None:
                 customer.update({'billing_address_id': ship_address.id})
            db.session.commit()


def save_billing_address(billing_form):
    current_cart = get_current_pending_cart()
    if current_cart:
        billing_address = persist_address(billing_form)
        customer = get_current_customer()
        if customer and billing_address:
            customer.update({'billing_address_id': billing_address.id})
            db.session.commit()


def persist_address(form):
    address = Address(
                first_name = form.first_name.data,
                last_name = form.last_name.data,
                address1 = form.address1.data,
                address2 = form.address2.data,
                city = form.city.data,
                state = form.state.data,
                zip = form.zip.data,
                email = form.email.data,
                phone = form.phone.data
        )
    db.session.add(address)
    db.session.flush()
    db.session.commit()
    return address