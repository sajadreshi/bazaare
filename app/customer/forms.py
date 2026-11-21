from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length

from app.checkout.forms import BillingForm as CheckoutBillingForm
from app.checkout.forms import ShippingForm as CheckoutShippingForm
from app.services.account import MIN_PASSWORD_LENGTH, PROFILE_FIELDS


class ProfileForm(FlaskForm):
    first_name = StringField(
        "First Name", validators=[Length(max=100), DataRequired()], render_kw={"placeholder": "First Name"}
    )
    last_name = StringField(
        "Last Name", validators=[Length(max=100), DataRequired()], render_kw={"placeholder": "Last Name"}
    )
    cell_number = StringField(
        "Cell Phone", validators=[Length(max=20)], render_kw={"placeholder": "Cell Phone"}
    )
    marketing_email = BooleanField("Marketing Email", render_kw={"placeholder": "Receive Marketing email"})
    transactional_email = BooleanField(
        "Transactional Email", render_kw={"placeholder": "Receive Transactional email"}
    )
    marketing_sms = BooleanField("Marketing SMS", render_kw={"placeholder": "Receive Marketing SMS"})
    transactional_sms = BooleanField(
        "Transactional SMS", render_kw={"placeholder": "Receive Transactional SMS"}
    )
    submit = SubmitField("Save")

    def fill_from(self, user):
        if not self.is_submitted():
            for field in PROFILE_FIELDS:
                getattr(self, field).data = getattr(user, field)
        return self


class ShippingForm(CheckoutShippingForm):
    submit = SubmitField("Save")


class BillingForm(CheckoutBillingForm):
    submit = SubmitField("Save")


class ChangePassword(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=MIN_PASSWORD_LENGTH, message=f"Use at least {MIN_PASSWORD_LENGTH} characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Change Password")
