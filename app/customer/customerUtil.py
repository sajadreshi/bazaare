from flask_login import current_user

from app.extension import db
from app.models import Cart, Customer, User


def findCurrentCustomer():
    return Customer.query.filter_by(user_id=current_user.id).first()


def updatePassword(changePasswordForm):
    user = User.query.filter_by(id=current_user.id).first()
    user.set_password(changePasswordForm.password.data)
    db.session.flush()
    db.session.commit()
    return user


def fetchOrdersForCustomer():
    orders = (
        db.session.query(Cart)
        .filter(Cart.customer_id == current_user.id, Cart.status.in_(["COMPLETED", "DELIVERED", "CANCELLED"]))
        .all()
    )
    return orders
