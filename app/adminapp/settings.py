"""Admin > Settings: shop-wide inventory rules."""

from flask import flash, redirect, url_for
from flask_admin import BaseView, expose
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import BooleanField, DecimalField, IntegerField, StringField
from wtforms.validators import Email, InputRequired, Length, NumberRange, Optional

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


class TaxesView(AdminOnlyMixin, BaseView):
    """Settings > Taxes: where the shop collects sales tax, the ZIP rate table and what was collected."""

    @expose("/", methods=["GET", "POST"])
    def index(self):
        from decimal import Decimal, InvalidOperation

        from flask import request

        from app.models import Address, Order, TaxRate, TaxState
        from app.services import tax
        from app.us_states import US_STATES

        if request.method == "POST":
            action = request.form.get("action")
            if action == "upload":
                upload = request.files.get("rates")
                if not upload or not upload.filename:
                    flash("Choose the rate file (.csv) to upload.", "error")
                else:
                    try:
                        counts = tax.load_rates(upload.read(), source=upload.filename)
                    except tax.RateFileError as error:
                        db.session.rollback()
                        flash(f"That file couldn't be loaded: {error}", "error")
                    else:
                        db.session.commit()
                        summary = ", ".join(f"{state}: {n} ZIP codes" for state, n in counts.items())
                        flash(f"Rates loaded ({summary}).", "success")
            elif action == "save":
                errors = []
                for state in db.session.query(TaxState):
                    key = state.state
                    state.collect = request.form.get(f"collect-{key}") == "y"
                    state.tax_shipping = request.form.get(f"shipping-{key}") == "y"
                    raw = (request.form.get(f"fallback-{key}") or "").strip().rstrip("%")
                    try:
                        rate = Decimal(raw or "0") / 100
                        if not Decimal(0) <= rate < Decimal("0.5"):
                            raise InvalidOperation
                        state.fallback_rate = rate
                    except InvalidOperation:
                        errors.append(f"{key}: “{raw}” isn't a percentage.")
                new = (request.form.get("add_state") or "").strip().upper()
                if new and db.session.get(TaxState, new) is None:
                    db.session.add(TaxState(state=new, collect=True, tax_shipping=True, fallback_rate=0))
                if errors:
                    db.session.rollback()
                    for error in errors:
                        flash(error, "error")
                else:
                    db.session.commit()
                    flash("Tax settings saved.", "success")
            return redirect(url_for(".index"))

        states = db.session.query(TaxState).order_by(TaxState.collect.desc(), TaxState.state).all()
        zip_counts = dict(
            db.session.query(TaxRate.state, func.count(TaxRate.zip)).group_by(TaxRate.state).all()
        )
        lookup_zip = (request.args.get("zip") or "").strip()
        lookup = None
        if lookup_zip:
            state = (request.args.get("state") or "").strip().upper()
            if not state:
                row = db.session.get(TaxRate, tax.zip5(lookup_zip) or "")
                state = row.state if row else "NY"
            lookup = (state, tax.quote(Address(state=state, zip=lookup_zip)))

        report = (
            db.session.query(
                func.extract("year", Order.placed_at),
                func.extract("month", Order.placed_at),
                Order.tax_state,
                func.count(Order.id),
                func.sum(Order.total_merchandise),
                func.sum(Order.total_shipping),
                func.sum(Order.total_taxes),
                func.sum(Order.shipping_tax),
            )
            .filter(Order.status != "CANCELLED", Order.tax_state.isnot(None))
            .group_by(
                func.extract("year", Order.placed_at), func.extract("month", Order.placed_at), Order.tax_state
            )
            .order_by(
                func.extract("year", Order.placed_at).desc(), func.extract("month", Order.placed_at).desc()
            )
            .limit(36)
            .all()
        )
        names = dict(US_STATES)
        return self.render(
            "admin/taxes.html",
            states=states,
            zip_counts=zip_counts,
            stale={s.state for s in tax.stale_states()},
            lookup_zip=lookup_zip,
            lookup=lookup,
            report=report,
            state_names=names,
            addable=[(code, name) for code, name in US_STATES if code not in {s.state for s in states}],
        )


class PromotionSettingsForm(FlaskForm):
    free_shipping_over = DecimalField(
        "Free standard shipping when the bag reaches ($)",
        places=2,
        validators=[Optional(), NumberRange(min=0, max=100000)],
    )
    coupons_enabled = BooleanField("Show the “Have a coupon code?” box at checkout")


class PromotionSettingsView(AdminOnlyMixin, BaseView):
    """Promotions > Free shipping & coupons: the free-shipping amount and the coupon box switch."""

    @expose("/", methods=["GET", "POST"])
    def index(self):
        settings = inventory.settings()
        form = PromotionSettingsForm(obj=settings)
        if form.validate_on_submit():
            form.populate_obj(settings)
            inventory.forget_settings()
            db.session.commit()
            flash(
                "Promotion settings saved. Open bags are re-priced the next time they're viewed.", "success"
            )
            return redirect(url_for(".index"))
        db.session.commit()
        return self.render("admin/promotion_settings.html", form=form, settings=settings)


class EmailSettingsForm(FlaskForm):
    order_alert_email = StringField(
        "Send new-order alerts to", validators=[Optional(), Email(), Length(max=120)]
    )
    support_email = StringField(
        "Customer support address", validators=[InputRequired(), Email(), Length(max=120)]
    )


class EmailsView(AdminOnlyMixin, BaseView):
    """Settings > Emails: where order alerts go, the support address, and previews of every order email."""

    @expose("/", methods=["GET", "POST"])
    def index(self):
        from flask import current_app, request

        from app import mailer
        from app.models import Order
        from app.services import notifications

        settings = inventory.settings()
        form = EmailSettingsForm(obj=settings)
        if request.method == "POST" and request.form.get("action") == "test":
            order = db.session.query(Order).order_by(Order.id.desc()).first()
            to = notifications.alert_address()
            if order is None or not to:
                flash("There's no order to use for a test yet, or no alert address.", "error")
            else:
                email = notifications.build("confirmed", order)
                mailer.send("[Test] " + email.subject, [to], email.html, email.text)
                where = "saved to the outbox folder" if mailer.uses_outbox(current_app) else f"sent to {to}"
                flash(f"Test email {where}.", "success")
            return redirect(url_for(".index"))
        if form.validate_on_submit():
            form.populate_obj(settings)
            settings.order_alert_email = settings.order_alert_email or None
            inventory.forget_settings()
            db.session.commit()
            flash("Email settings saved.", "success")
            return redirect(url_for(".index"))
        db.session.commit()
        latest = db.session.query(Order).order_by(Order.id.desc()).first()
        return self.render(
            "admin/emails.html",
            form=form,
            latest=latest,
            kinds=notifications.KINDS,
            mail_server=current_app.config.get("MAIL_SERVER"),
            outbox=mailer.outbox_dir(current_app) if mailer.uses_outbox(current_app) else None,
            alert_to=notifications.alert_address(),
        )

    @expose("/preview/<kind>/<int:order_id>")
    def preview(self, kind, order_id):
        from flask import abort

        from app.models import Order
        from app.services import notifications

        order = db.session.get(Order, order_id)
        if order is None or kind not in notifications.KINDS:
            abort(404)
        return notifications.build(kind, order).html


REPORT_TABS = {
    "sales": "Sales",
    "products": "Products",
    "categories": "Categories",
    "coupons": "Coupons",
    "customers": "Customers",
    "inventory": "Inventory value",
    "tax": "Tax",
}


class ReportsView(AdminOnlyMixin, BaseView):
    """Reports: sales over a date range, by product, category, coupon and customer; stock value; tax."""

    @expose("/")
    def index(self):
        from flask import request

        from app.services import reports

        tab = request.args.get("tab", "sales")
        if tab not in REPORT_TABS:
            tab = "sales"
        rng = reports.parse_range(request.args)
        data = {}
        if tab == "sales":
            data["report"] = reports.sales(rng)
        elif tab == "products":
            data["ranked"], data["unsold"] = reports.products(rng)
        elif tab == "categories":
            data["rows"] = reports.categories(rng)
        elif tab == "coupons":
            data["rows"], data["without"] = reports.coupons(rng)
        elif tab == "customers":
            data["report"] = reports.customers(rng)
        elif tab == "inventory":
            data["rows"], data["units"], data["value"] = reports.inventory(rng)
        elif tab == "tax":
            data["rows"] = reports.tax(rng)
        query = {k: v for k, v in request.args.items() if k != "tab"}
        return self.render(
            "admin/reports.html",
            tab=tab,
            tabs=REPORT_TABS,
            rng=rng,
            presets=reports.PRESETS,
            groups=reports.GROUPS,
            query=query,
            **data,
        )

    @expose("/<tab>.csv")
    def download(self, tab):
        from flask import Response, abort, request

        from app.services import reports

        if tab not in REPORT_TABS:
            abort(404)
        filename, text = reports.csv_for(tab, reports.parse_range(request.args))
        return Response(
            text,
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
