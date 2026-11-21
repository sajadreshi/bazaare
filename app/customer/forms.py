from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from app.us_states import US_STATES


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


class ShippingForm(FlaskForm):
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
    form_id = HiddenField("FormId", default="shipping_form")
    submit = SubmitField("Continue")


class BillingForm(FlaskForm):
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
    form_id = HiddenField("FormId", default="billing_form")
    submit = SubmitField("Save")


class ChangePassword(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Change Password")


def populateProfileForm(proform, user):
    if user:
        proform.first_name.data = user.first_name
        proform.last_name.data = user.last_name
        proform.cell_number.data = user.cell_number
        proform.marketing_email.data = user.marketing_email
        proform.transactional_email.data = user.transactional_email
        proform.marketing_sms.data = user.marketing_sms
        proform.transactional_sms.data = user.transactional_sms

    return proform


def populateBillingAddressForm(billingAddressForm, billingAddress):
    if billingAddress:
        billingAddressForm.first_name.data = billingAddress.first_name
        billingAddressForm.last_name.data = billingAddress.last_name
        billingAddressForm.address1.data = billingAddress.address1
        billingAddressForm.address2.data = billingAddress.address2
        billingAddressForm.city.data = billingAddress.city
        billingAddressForm.state.data = billingAddress.state
        billingAddressForm.zip.data = billingAddress.zip
        billingAddressForm.email.data = billingAddress.email
        billingAddressForm.phone.data = billingAddress.phone
    return billingAddressForm


def populateshippingAddressForm(shippingAddressForm, shippingAddress):
    if shippingAddress:
        shippingAddressForm.first_name.data = shippingAddress.first_name
        shippingAddressForm.last_name.data = shippingAddress.last_name
        shippingAddressForm.address1.data = shippingAddress.address1
        shippingAddressForm.address2.data = shippingAddress.address2
        shippingAddressForm.city.data = shippingAddress.city
        shippingAddressForm.state.data = shippingAddress.state
        shippingAddressForm.zip.data = shippingAddress.zip
        shippingAddressForm.email.data = shippingAddress.email
        shippingAddressForm.phone.data = shippingAddress.phone
    return shippingAddressForm
