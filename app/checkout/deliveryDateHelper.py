import datetime

from app.checkout.commonutil import DELIVERY_LEAD_DAYS, convertDate, get_current_pending_cart
from app.extension import db
from app.models import Holiday


def fetchDeliveryDays():
    delivery_dates = []
    start_date = datetime.date.today() + datetime.timedelta(DELIVERY_LEAD_DAYS)
    end_date = start_date + datetime.timedelta(90)
    off_days = getHolidays()
    for deldate in range((end_date - start_date).days + 1):
        result_date = start_date + datetime.timedelta(deldate)
        if getFormatedDate(result_date) not in off_days:
            delivery_dates.append((result_date, result_date.strftime("%a, %d  %b  %Y")))
    return delivery_dates


def getHolidays():
    formatted_holidays = []
    current_date = datetime.date.today()
    holidays = db.session.query(Holiday).filter(Holiday.holiday_date > current_date).all()
    for holiday in holidays:
        formatted_holidays.append(getFormatedDate(holiday.holiday_date))
    return formatted_holidays


def getFormatedDate(dttm):
    if not hasattr(dttm, "strftime"):
        return dttm
    return dttm.strftime("%m-%d-%Y")


def saveDeliveryDate(delivery_form):
    current_cart = get_current_pending_cart()
    if current_cart:
        deliveryDate = convertDate(delivery_form.delivery_date.data, "%Y-%m-%d")
        current_cart.update(
            {"delivery_date": deliveryDate, "delivery_window": delivery_form.delivery_window.data}
        )
        db.session.commit()
