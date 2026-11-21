from threading import Thread
from flask import current_app
from flask import render_template
from flask_mail import Message
from app import mail
from time import sleep





def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Bazaare] Reset Your Password',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/resetPassword.txt',
                                         user=user, token=token),
               html_body=render_template('email/resetPasswordEmail.html',
                                         user=user, token=token))


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject,sender,recipients,text_body,html_body):
    app = current_app._get_current_object()
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.text = text_body
    msg.html = html_body
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
