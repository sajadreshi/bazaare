from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

from app.checkout.forms import BillingForm as CheckoutBillingForm
from app.checkout.forms import ShippingForm as CheckoutShippingForm
from app.services.account import MIN_PASSWORD_LENGTH, PROFILE_FIELDS


class ProfileForm(FlaskForm):
    first_name = StringField("First name", validators=[Length(max=100), DataRequired()])
    last_name = StringField("Last name", validators=[Length(max=100), DataRequired()])
    cell_number = StringField("Mobile number", validators=[Length(max=20)])
    marketing_email = BooleanField("New arrivals and offers by email")
    transactional_email = BooleanField("Order updates by email")
    marketing_sms = BooleanField("New arrivals and offers by text message")
    transactional_sms = BooleanField("Order updates by text message")
    submit = SubmitField("Save changes")

    def fill_from(self, user):
        if not self.is_submitted():
            for field in PROFILE_FIELDS:
                getattr(self, field).data = getattr(user, field)
        return self


class ShippingForm(CheckoutShippingForm):
    submit = SubmitField("Save address")


class BillingForm(CheckoutBillingForm):
    submit = SubmitField("Save address")


class ChangePassword(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField(
        "New password",
        validators=[
            DataRequired(),
            Length(min=MIN_PASSWORD_LENGTH, message=f"Use at least {MIN_PASSWORD_LENGTH} characters."),
        ],
    )
    confirm_password = PasswordField(
        "Repeat new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Change password")
