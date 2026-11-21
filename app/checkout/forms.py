from flask_wtf import FlaskForm
from wtforms import HiddenField, RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.services.checkout import ADDRESS_FIELDS
from app.services.payments import PAYMENT_METHODS
from app.services.shipping import METHODS, estimated_delivery, method_for
from app.us_states import US_STATES


class _AddressForm(FlaskForm):
    first_name = StringField(
        "First Name", validators=[Length(max=100), DataRequired()], render_kw={"placeholder": "First Name"}
    )
    last_name = StringField(
        "Last Name", validators=[Length(max=100), DataRequired()], render_kw={"placeholder": "Last Name"}
    )
    address1 = StringField(
        "Address Line1", validators=[DataRequired()], render_kw={"placeholder": "Address Line 1"}
    )
    address2 = StringField("Address Line2", render_kw={"placeholder": "Address Line 2 (Optional)"})
    city = StringField("City", validators=[DataRequired()], render_kw={"placeholder": "City"})
    state = SelectField("State", validators=[DataRequired()], choices=US_STATES)
    zip = StringField("Zip", validators=[Length(max=10), DataRequired()], render_kw={"placeholder": "Zip"})
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"placeholder": "Email"})
    phone = StringField(
        "Phone", validators=[Length(max=14), DataRequired()], render_kw={"placeholder": "Phone"}
    )
    submit = SubmitField("Continue")

    def fill_from(self, address):
        """Pre-fill the form from an Address on GET (never overwrites submitted data)."""
        if address is not None and not self.is_submitted():
            for field in ADDRESS_FIELDS:
                getattr(self, field).data = getattr(address, field)
        return self


class ShippingForm(_AddressForm):
    form_id = HiddenField("FormId", default="shipping_form")


class BillingForm(_AddressForm):
    form_id = HiddenField("FormId", default="billing_form")


class ShippingMethodForm(FlaskForm):
    shipping_method = RadioField("Shipping method", validators=[DataRequired()], choices=[])
    form_id = HiddenField("FormId", default="shipping_method_form")
    submit = SubmitField("Continue")

    def fill_from(self, cart):
        merchandise = cart.total_merchandise if cart and cart.total_merchandise is not None else 0
        self.shipping_method.choices = []
        for method in METHODS.values():
            charge = method.charge(merchandise)
            earliest, latest = estimated_delivery(method.code)
            price = "Free" if not charge else f"${charge:.2f}"
            arrives = f"arrives {earliest:%a %d %b}–{latest:%a %d %b}"
            label = f"{method.name}: {price} · {method.days_label} ({arrives})"
            self.shipping_method.choices.append((method.code, label))
        if not self.is_submitted():
            self.shipping_method.data = method_for(cart.shipping_method if cart else None).code
        return self


class PlaceOrderForm(FlaskForm):
    payment_method = SelectField("Payment Method", validators=[DataRequired()], choices=PAYMENT_METHODS)
    form_id = HiddenField("FormId", default="place_order_form")
    submit = SubmitField("Place Order")
