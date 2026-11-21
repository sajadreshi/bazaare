import os

class Config(object):
   SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-change-me'
   SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or "sqlite:///bazaare.db"
   FLASK_ADMIN_SWATCH = 'cyborg'
   MAIL_SERVER = 'localhost'
   MAIL_PORT='25'
   ADMINS = ['your-email@example.com']
