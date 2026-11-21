from flask_admin import Admin
from flask_ckeditor import CKEditor
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.adminapp.security import SecureIndexView

login_manager = LoginManager()
login_manager.login_view = "auth.login"
db = SQLAlchemy()
admin = Admin(index_view=SecureIndexView())
migrate = Migrate()
ckeditor = CKEditor()
mail = Mail()
csrf = CSRFProtect()
