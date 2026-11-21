"""Access control shared by every Flask-Admin view (kept free of model imports)."""

from flask import redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib import sqla
from flask_login import current_user


def is_admin_user():
    return bool(current_user.is_authenticated and any(r.name.lower() == "admin" for r in current_user.roles))


class AdminOnlyMixin:
    """Only users with the admin role may see a view; others are sent to login."""

    def is_accessible(self):
        return is_admin_user()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_auth.login", next=request.full_path.rstrip("?")))


class SecureIndexView(AdminOnlyMixin, AdminIndexView):
    """The admin's landing page: a dashboard of sales, orders to ship and catalog to-dos."""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "Dashboard")
        super().__init__(**kwargs)

    @expose("/")
    def index(self):
        from app.services.dashboard import build_dashboard  # imported late: models import this module's app

        return self.render("admin/index.html", dash=build_dashboard())


class SecureModelView(AdminOnlyMixin, sqla.ModelView):
    # CSRF for admin forms comes from the app-wide CSRFProtect: Flask-Admin's
    # templates add csrf_token() to every create/edit/delete/action form.
    # (Don't also use flask_admin.form.SecureForm: it adds a second, clashing token.)
    column_hide_backrefs = False
