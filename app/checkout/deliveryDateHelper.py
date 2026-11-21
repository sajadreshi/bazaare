from app import db
import datetime
from app.models import Holiday
from app.checkout.commonutil import get_current_pending_cart,convertDate

def fetchDeliveryDays():
    delivery_dates = []
    try:
        start_date = datetime.date.today() + datetime.timedelta(3)
        end_date = start_date + datetime.timedelta(90)
        off_days = getHolidays()
        for deldate in range((end_date - start_date).days + 1):
            result_date = start_date + datetime.timedelta(deldate)
            if not getFormatedDate(result_date) in off_days:
              formatted_date = result_date.strftime("%a, %d  %b  %Y")
              final_date =(result_date,formatted_date)
              delivery_dates.append(final_date)
        print(delivery_dates) 
    except:
      return delivery_dates
    return delivery_dates

def getHolidays():
    formatted_holidays = []
    current_date = datetime.date.today()
    holidays = db.session.query(Holiday).filter(Holiday.holiday_date > current_date).all()
    for holiday in holidays:
      formatted_holidays.append(getFormatedDate(holiday.holiday_date))
    return formatted_holidays


def getFormatedDate(dttm):
  try:
    formatted_date = dttm.strftime("%m-%d-%Y")
    return formatted_date
  except:
    return dttm
  
def saveDeliveryDate(delivery_form):
    current_cart = get_current_pending_cart()
    if current_cart:
       deliveryDate = convertDate(delivery_form.delivery_date.data,'%Y-%m-%d')
       current_cart.update({'delivery_date': deliveryDate,'delivery_window':delivery_form.delivery_window.data})
       db.session.commit()
        