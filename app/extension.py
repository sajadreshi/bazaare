from flask_admin import Admin
from flask_ckeditor import CKEditor
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
db = SQLAlchemy()
admin = Admin()
migrate = Migrate()
ckeditor = CKEditor()
mail = Mail()
