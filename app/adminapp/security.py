"""Access control shared by every Flask-Admin view (kept free of model imports)."""

from flask import redirect, request, url_for
from flask_admin import AdminIndexView
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
    pass


class SecureModelView(AdminOnlyMixin, sqla.ModelView):
    # CSRF for admin forms comes from the app-wide CSRFProtect: Flask-Admin's
    # templates add csrf_token() to every create/edit/delete/action form.
    # (Don't also use flask_admin.form.SecureForm: it adds a second, clashing token.)
    column_hide_backrefs = False
