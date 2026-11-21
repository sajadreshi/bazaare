from flask_login import current_user

from app.extension import db
from app.models import User


def updateProfile(proForm):
    user = getCUrrentUser()
    user.update(
        {
            "first_name": proForm.first_name.data,
            "last_name": proForm.last_name.data,
            "cell_number": proForm.cell_number.data,
            "marketing_email": proForm.marketing_email.data,
            "transactional_email": proForm.transactional_email.data,
            "marketing_sms": proForm.marketing_sms.data,
            "transactional_sms": proForm.transactional_sms.data,
        }
    )
    db.session.commit()
    return user


def getCUrrentUser():
    return User.query.filter_by(id=current_user.id)


def getCurrentUserProfile():
    return getCUrrentUser().first()
