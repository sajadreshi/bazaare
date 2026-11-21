from app.customer.customerUtil import findCurrentCustomer
from app.extension import db
from app.models import Address


def updateBillingAddress(billingForm):
    if billingForm:
        billing_address = persist_address(billingForm)
        customer = findCurrentCustomer()
        if customer and billing_address:
            customer.billing_address_id = billing_address.id
            db.session.commit()
            return billing_address
    return None


def updateShippingAddress(shippingForm):
    if shippingForm:
        shipping_address = persist_address(shippingForm)
        customer = findCurrentCustomer()
        if customer and shipping_address:
            customer.shipping_address_id = shipping_address.id
            db.session.commit()
            return shipping_address
    return None


def getCurrentBillingAddress():
    customer = findCurrentCustomer()
    if customer and customer.billing_address_id:
        return Address.query.filter_by(id=customer.billing_address_id).first()
    return


def getCurrentShippingAddress():
    customer = findCurrentCustomer()
    if customer and customer.shipping_address_id:
        return Address.query.filter_by(id=customer.shipping_address_id).first()
    return None


def persist_address(form):
    address = Address(
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        address1=form.address1.data,
        address2=form.address2.data,
        city=form.city.data,
        state=form.state.data,
        zip=form.zip.data,
        email=form.email.data,
        phone=form.phone.data,
    )
    db.session.add(address)
    db.session.flush()
    db.session.commit()
    return address
