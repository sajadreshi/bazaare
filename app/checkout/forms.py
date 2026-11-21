from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.services.checkout import ADDRESS_FIELDS, DELIVERY_WINDOWS, delivery_dates
from app.services.payments import PAYMENT_METHODS
from app.us_states import US_STATES

DATE_LABEL = "%a, %d  %b  %Y"


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


class DeliveryDateForm(FlaskForm):
    delivery_date = SelectField(
        "Delivery Date", validators=[DataRequired()], choices=[], validate_choice=False
    )
    delivery_window = SelectField(
        "Delivery Window", validators=[DataRequired()], choices=[(w, w) for w in DELIVERY_WINDOWS]
    )
    form_id = HiddenField("FormId", default="delivery_form")
    submit = SubmitField("Continue")

    def fill_from(self, cart):
        self.delivery_date.choices = [(d.isoformat(), d.strftime(DATE_LABEL)) for d in delivery_dates()]
        if cart is not None and not self.is_submitted():
            if cart.delivery_date:
                self.delivery_date.data = cart.delivery_date.date().isoformat()
            if cart.delivery_window:
                self.delivery_window.data = cart.delivery_window
        return self


class PlaceOrderForm(FlaskForm):
    payment_method = SelectField("Payment Method", validators=[DataRequired()], choices=PAYMENT_METHODS)
    form_id = HiddenField("FormId", default="place_order_form")
    submit = SubmitField("Place Order")
