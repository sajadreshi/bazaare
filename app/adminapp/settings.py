"""Admin > Settings: shop-wide inventory rules."""

from flask import flash, redirect, url_for
from flask_admin import BaseView, expose
from flask_wtf import FlaskForm
from wtforms import IntegerField
from wtforms.validators import InputRequired, NumberRange

from app.adminapp.security import AdminOnlyMixin
from app.extension import db
from app.services import inventory


class InventorySettingsForm(FlaskForm):
    stock_threshold = IntegerField(
        "Take an option off sale when its stock reaches",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )
    low_stock_alert = IntegerField(
        "Warn me when this many or fewer are left to sell",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )


class SettingsView(AdminOnlyMixin, BaseView):
    @expose("/", methods=["GET", "POST"])
    def index(self):
        settings = inventory.settings()
        form = InventorySettingsForm(obj=settings)
        if form.validate_on_submit():
            form.populate_obj(settings)
            inventory.forget_settings()
            hidden, restored = inventory.refresh_all()
            db.session.commit()
            message = "Settings saved."
            if hidden:
                message += f" {len(hidden)} product(s) are now sold out and hidden from the shop."
            if restored:
                message += f" {len(restored)} product(s) are available again and back in the shop."
            flash(message, "success")
            return redirect(url_for(".index"))
        db.session.commit()  # keeps the settings row if it was just created
        return self.render("admin/settings.html", form=form, settings=settings)


class StockView(AdminOnlyMixin, BaseView):
    """Every option's stock on one page, for counting and restocking in one go."""

    @expose("/", methods=["GET", "POST"])
    def index(self):
        from flask import request

        from app.models import Product, Variant

        if request.method == "POST":
            # The app-wide CSRFProtect has already checked this POST's token.
            changed, errors = set(), []
            fill = (request.form.get("fill_missing") or "").strip()
            if fill:
                if not fill.isdigit():
                    flash(f"“{fill}” isn't a whole number.", "error")
                    return redirect(url_for(".index", show=request.args.get("show", "all")))
                for variant in db.session.query(Variant).filter(Variant.stock.is_(None)):
                    variant.stock = int(fill)
                    changed.add(variant.product)
            for variant in db.session.query(Variant).all():
                raw = request.form.get(f"stock-{variant.id}")
                if raw is None:
                    continue
                raw = raw.strip()
                if raw == "":
                    continue
                if not raw.isdigit():
                    errors.append(f"{variant.product.name} ({variant.name}): “{raw}” isn't a whole number.")
                    continue
                if variant.stock != int(raw):
                    variant.stock = int(raw)
                    changed.add(variant.product)
            if errors:
                db.session.rollback()
                for error in errors:
                    flash(error, "error")
                return redirect(url_for(".index", show=request.args.get("show", "all")))
            hidden, restored = inventory.refresh(changed)
            db.session.commit()
            message = f"Stock saved for {len(changed)} product(s)." if changed else "Nothing changed."
            if hidden:
                message += f" Hidden (sold out): {', '.join(p.name for p in hidden)}."
            if restored:
                message += f" Back in the shop: {', '.join(p.name for p in restored)}."
            flash(message, "success")
            return redirect(url_for(".index", show=request.args.get("show", "all")))

        show = request.args.get("show", "all")
        products = db.session.query(Product).order_by(Product.name).all()
        rows = []
        for product in products:
            for option in product.options:
                available = option.available
                state = (
                    "missing"
                    if option.stock is None
                    else "out"
                    if available == 0
                    else "low"
                    if available <= inventory.low_stock_alert()
                    else "ok"
                )
                rows.append((product, option, state))
        counts = {s: sum(1 for *_, st in rows if st == s) for s in ("missing", "out", "low", "ok")}
        if show != "all":
            rows = [r for r in rows if r[2] == show]
        return self.render(
            "admin/stock.html", rows=rows, show=show, counts=counts, settings=inventory.settings()
        )
