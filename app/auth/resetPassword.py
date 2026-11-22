from flask import render_template

from app import mailer


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    mailer.send(
        "Reset your BazaarE' password",
        [user.email],
        html=render_template("email/resetPasswordEmail.html", user=user, token=token),
        text=render_template("email/resetPassword.txt", user=user, token=token),
    )
