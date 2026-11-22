"""Sales reports for the admin: sales over time, products, categories, coupons, customers,
inventory value and tax. Dates are in the shop's time zone (New York).

Only placed, shipped and delivered orders count; cancelled orders are reported separately.
Money comes from what the orders actually charged (order and order-line snapshots).
"""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.extension import db
from app.models import Address, Order, OrderItem, Product, utcnow

SHOP_TZ = ZoneInfo("America/New_York")
ZERO = Decimal("0.00")
COUNTED = ("PLACED", "SHIPPED", "DELIVERED")

PRESETS = {
    "today": "Today",
    "last_7": "Last 7 days",
    "last_30": "Last 30 days",
    "this_month": "This month",
    "last_month": "Last month",
    "this_year": "This year",
    "last_year": "Last year",
    "custom": "Custom dates",
}
GROUPS = {"day": "By day", "week": "By week", "month": "By month"}


def local(dt):
    """A naive UTC datetime as a naive New York datetime."""
    return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(SHOP_TZ).replace(tzinfo=None)


def _utc(day):
    """Midnight New York time at the start of ``day``, as naive UTC."""
    return (
        datetime.combine(day, time()).replace(tzinfo=SHOP_TZ).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    )


@dataclass
class Range:
    start: date
    end: date  # inclusive
    preset: str = "custom"
    group: str = "day"

    @property
    def label(self):
        if self.start == self.end:
            return self.start.strftime("%d %b %Y")
        return f"{self.start:%d %b %Y} – {self.end:%d %b %Y}"

    @property
    def days(self):
        return (self.end - self.start).days + 1

    @property
    def utc_bounds(self):
        return _utc(self.start), _utc(self.end + timedelta(days=1))

    def previous(self):
        """The same length of time just before this range (for comparisons)."""
        if self.preset == "last_month" or self.preset == "this_month":
            end = self.start - timedelta(days=1)
            return Range(end.replace(day=1), end, "custom", self.group)
        return Range(
            self.start - timedelta(days=self.days), self.start - timedelta(days=1), "custom", self.group
        )


def parse_range(args, today=None):
    today = today or local(utcnow()).date()
    preset = args.get("range") or "this_month"
    if preset not in PRESETS:
        preset = "this_month"
    if preset == "today":
        start = end = today
    elif preset == "last_7":
        start, end = today - timedelta(days=6), today
    elif preset == "last_30":
        start, end = today - timedelta(days=29), today
    elif preset == "this_month":
        start, end = today.replace(day=1), today
    elif preset == "last_month":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    elif preset == "this_year":
        start, end = today.replace(month=1, day=1), today
    elif preset == "last_year":
        start, end = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    else:
        try:
            start = date.fromisoformat(args.get("start", ""))
            end = date.fromisoformat(args.get("end", ""))
        except ValueError:
            start, end = today.replace(day=1), today
        if end < start:
            start, end = end, start
    group = args.get("group")
    if group not in GROUPS:
        days = (end - start).days + 1
        group = "day" if days <= 45 else "week" if days <= 200 else "month"
    return Range(start, end, preset, group)


def orders_in(rng, statuses=COUNTED):
    begin, finish = rng.utc_bounds
    return (
        db.session.query(Order)
        .filter(Order.placed_at >= begin, Order.placed_at < finish, Order.status.in_(statuses))
        .order_by(Order.placed_at)
        .all()
    )


def _money(values):
    return sum((Decimal(v or 0) for v in values), ZERO)


# ---------------------------------------------------------------- sales summary


@dataclass
class Totals:
    orders: int = 0
    items: int = 0
    gross: Decimal = ZERO  # merchandise at the prices charged, before discounts
    discounts: Decimal = ZERO
    shipping: Decimal = ZERO
    tax: Decimal = ZERO
    total: Decimal = ZERO  # what customers paid

    @property
    def net(self):
        """Merchandise sales after discounts (excludes shipping and tax)."""
        return self.gross - self.discounts

    @property
    def average(self):
        return (self.total / self.orders).quantize(Decimal("0.01")) if self.orders else ZERO

    def add(self, order):
        self.orders += 1
        self.items += len(order.items)
        self.gross += Decimal(order.total_merchandise or 0)
        self.discounts += Decimal(order.total_discount or 0)
        self.shipping += Decimal(order.total_shipping or 0)
        self.tax += Decimal(order.total_taxes or 0)
        self.total += Decimal(order.total or 0)


def _period_start(day, group):
    if group == "week":
        return day - timedelta(days=day.weekday())  # Monday
    if group == "month":
        return day.replace(day=1)
    return day


def _period_label(start, group):
    if group == "week":
        return f"Week of {start:%d %b}"
    if group == "month":
        return start.strftime("%b %Y")
    return start.strftime("%a %d %b")


@dataclass
class SalesReport:
    rng: Range
    totals: Totals
    previous: Totals
    periods: list  # [(label, Totals)]
    cancelled: int
    cancelled_total: Decimal
    peak: Decimal = field(default=ZERO)

    def change(self, attr):
        """Percentage change against the previous period, or None."""
        now, before = getattr(self.totals, attr), getattr(self.previous, attr)
        if not before:
            return None
        return int(round((Decimal(now) - Decimal(before)) / Decimal(before) * 100))


def sales(rng):
    totals, periods = Totals(), {}
    day = _period_start(rng.start, rng.group)
    while day <= rng.end:  # every period appears, even with no sales
        periods[day] = Totals()
        day = (
            (day + timedelta(days=1))
            if rng.group == "day"
            else (
                day + timedelta(days=7)
                if rng.group == "week"
                else (day.replace(day=28) + timedelta(days=4)).replace(day=1)
            )
        )
    for order in orders_in(rng):
        totals.add(order)
        periods.setdefault(_period_start(local(order.placed_at).date(), rng.group), Totals()).add(order)
    previous = Totals()
    for order in orders_in(rng.previous()):
        previous.add(order)
    cancelled = orders_in(rng, statuses=("CANCELLED",))
    rows = [(_period_label(start, rng.group), t) for start, t in sorted(periods.items())]
    return SalesReport(
        rng=rng,
        totals=totals,
        previous=previous,
        periods=rows,
        cancelled=len(cancelled),
        cancelled_total=_money(o.total for o in cancelled),
        peak=max((t.net for _, t in rows), default=ZERO) or Decimal(1),
    )


# ---------------------------------------------------------------- products, options, categories


@dataclass
class ProductRow:
    key: str
    name: str
    sku: str
    product_id: int = None
    units: int = 0
    revenue: Decimal = ZERO  # after discounts
    orders: set = field(default_factory=set)
    options: dict = field(default_factory=lambda: defaultdict(lambda: [0, ZERO]))


def _lines(rng):
    begin, finish = rng.utc_bounds
    return (
        db.session.query(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.placed_at >= begin, Order.placed_at < finish, Order.status.in_(COUNTED))
        .all()
    )


def products(rng):
    rows = {}
    for line, order in _lines(rng):
        key = line.sku or line.name
        row = rows.setdefault(key, ProductRow(key, line.name, line.sku, line.product_id))
        amount = Decimal(line.price or 0) - Decimal(line.discount or 0)
        row.units += 1
        row.revenue += amount
        row.orders.add(order.id)
        option = line.variant_name if line.variant_name and line.variant_name != "One Size" else None
        if option:
            row.options[option][0] += 1
            row.options[option][1] += amount
    ranked = sorted(rows.values(), key=lambda r: (-r.revenue, -r.units, r.name))
    sold_ids = {r.product_id for r in rows.values() if r.product_id}
    unsold = (
        db.session.query(Product)
        .filter(Product.is_active.is_(True), ~Product.id.in_(sold_ids) if sold_ids else True)
        .order_by(Product.name)
        .all()
    )
    return ranked, unsold


def categories(rng):
    """Sales per category (a product in two categories counts in both), top-level first."""
    from app.adminapp.views import category_tree
    from app.models import Category

    per = defaultdict(lambda: [0, ZERO, set()])
    product_ids = set()
    for line, order in _lines(rng):
        if not line.product_id:
            continue
        product_ids.add(line.product_id)
        product = db.session.get(Product, line.product_id)
        if product is None:
            continue
        seen = set()
        for category in product.categories:
            for cat in (category, category.parent):
                if cat is not None and cat.id not in seen:
                    seen.add(cat.id)
                    per[cat.id][0] += 1
                    per[cat.id][1] += Decimal(line.price or 0) - Decimal(line.discount or 0)
                    per[cat.id][2].add(order.id)
    tree = category_tree(db.session.query(Category).all())
    return [
        (cat, depth, per[cat.id][0], per[cat.id][1], len(per[cat.id][2]))
        for cat, depth in tree
        if cat.id in per
    ]


# ---------------------------------------------------------------- coupons, customers


def coupons(rng):
    per = defaultdict(lambda: [0, ZERO, ZERO])  # orders, discount, net merchandise
    without = Totals()
    for order in orders_in(rng):
        if order.coupon_code:
            row = per[order.coupon_code]
            row[0] += 1
            row[1] += Decimal(order.total_discount or 0)
            row[2] += Decimal(order.total_merchandise or 0) - Decimal(order.total_discount or 0)
        else:
            without.add(order)
    rows = sorted(per.items(), key=lambda kv: -kv[1][0])
    return rows, without


@dataclass
class CustomerReport:
    new: int = 0
    returning: int = 0
    guest_orders: int = 0
    registered_orders: int = 0
    guest_sales: Decimal = ZERO
    registered_sales: Decimal = ZERO
    top: list = field(default_factory=list)  # [(name, email, kind, orders, spent)]
    places: list = field(default_factory=list)  # [(state, city, orders, spent)]


def customers(rng):
    from app.adminapp.views import order_customer

    orders = orders_in(rng)
    begin, _ = rng.utc_bounds
    report = CustomerReport()
    spend = {}
    places = defaultdict(lambda: [0, ZERO])
    counted = set()
    for order in orders:
        name, email, kind = order_customer(order)
        key = email.lower() if email else f"customer-{order.customer_id}"
        if key not in counted:
            counted.add(key)
            earlier = (
                db.session.query(Order.id)
                .filter(
                    Order.customer_id == order.customer_id, Order.placed_at < begin, Order.status.in_(COUNTED)
                )
                .first()
            )
            if earlier is None and email:  # a guest who ordered before with the same email
                earlier = (
                    db.session.query(Order.id)
                    .join(Address, Address.id == Order.shipping_address_id)
                    .filter(Order.placed_at < begin, Order.status.in_(COUNTED))
                    .filter(func.lower(Address.email) == email.lower())
                    .first()
                )
            if earlier is None:
                report.new += 1
            else:
                report.returning += 1
        total = Decimal(order.total or 0)
        if kind == "Registered":
            report.registered_orders += 1
            report.registered_sales += total
        else:
            report.guest_orders += 1
            report.guest_sales += total
        entry = spend.setdefault(key, [name, email, kind, 0, ZERO])
        entry[3] += 1
        entry[4] += total
        address = order.shipping_address
        if address is not None:
            place = places[(address.state, (address.city or "").title())]
            place[0] += 1
            place[1] += total
    report.top = sorted((tuple(v) for v in spend.values()), key=lambda r: -r[4])[:15]
    report.places = sorted(((s, c, n, t) for (s, c), (n, t) in places.items()), key=lambda r: -r[3])[:20]
    return report


# ---------------------------------------------------------------- inventory, tax


@dataclass
class StockRow:
    product: object
    in_stock: int
    available: int
    value: Decimal
    sold: int

    @property
    def sell_through(self):
        """Share of (sold + still in stock) that sold in the period, as a percentage."""
        base = self.sold + self.in_stock
        return int(round(self.sold * 100 / base)) if base else 0


def inventory(rng):
    sold = defaultdict(int)
    for line, _order in _lines(rng):
        if line.product_id:
            sold[line.product_id] += 1
    rows = []
    for product in db.session.query(Product).order_by(Product.name):
        stock = sum(o.stock or 0 for o in product.options)
        available = sum(o.available for o in product.options)
        value = _money(
            (o.stock or 0) * (o.price if o.price is not None else product.price) for o in product.options
        )
        rows.append(StockRow(product, stock, available, value, sold.get(product.id, 0)))
    total_units = sum(r.in_stock for r in rows)
    total_value = _money(r.value for r in rows)
    return rows, total_units, total_value


def tax(rng):
    per = defaultdict(
        lambda: [0, ZERO, ZERO, ZERO, ZERO]
    )  # orders, merchandise, shipping, tax, tax on shipping
    for order in orders_in(rng):
        if not order.tax_state:
            continue
        key = (local(order.placed_at).strftime("%Y-%m"), order.tax_state)
        row = per[key]
        row[0] += 1
        row[1] += Decimal(order.total_merchandise or 0) - Decimal(order.total_discount or 0)
        row[2] += Decimal(order.total_shipping or 0)
        row[3] += Decimal(order.total_taxes or 0)
        row[4] += Decimal(order.shipping_tax or 0)
    return sorted(((month, state, *values) for (month, state), values in per.items()), reverse=True)


# ---------------------------------------------------------------- CSV


def to_csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if v is None else (f"{v:.2f}" if isinstance(v, Decimal) else v) for v in row])
    return out.getvalue()


def csv_for(tab, rng):
    """(filename, csv text) for a report tab."""
    stamp = f"{rng.start:%Y%m%d}-{rng.end:%Y%m%d}"
    if tab == "sales":
        report = sales(rng)
        rows = [
            (label, t.orders, t.items, t.gross, t.discounts, t.net, t.shipping, t.tax, t.total, t.average)
            for label, t in report.periods
        ]
        t = report.totals
        rows.append(
            ("Total", t.orders, t.items, t.gross, t.discounts, t.net, t.shipping, t.tax, t.total, t.average)
        )
        header = [
            "Period",
            "Orders",
            "Items",
            "Gross sales",
            "Discounts",
            "Net sales",
            "Shipping",
            "Sales tax",
            "Total paid",
            "Average order",
        ]
    elif tab == "products":
        ranked, _ = products(rng)
        rows = [(r.name, r.sku, r.units, len(r.orders), r.revenue) for r in ranked]
        header = ["Product", "SKU", "Units sold", "Orders", "Revenue (after discounts)"]
    elif tab == "categories":
        rows = [
            ("  " * depth + cat.name, units, orders, revenue)
            for cat, depth, units, revenue, orders in categories(rng)
        ]
        header = ["Category", "Units sold", "Orders", "Revenue (after discounts)"]
    elif tab == "coupons":
        coupon_rows, without = coupons(rng)
        rows = [(code, n, discount, net) for code, (n, discount, net) in coupon_rows]
        rows.append(("(no coupon)", without.orders, ZERO, without.net))
        header = ["Coupon", "Orders", "Discount given", "Net merchandise sales"]
    elif tab == "customers":
        report = customers(rng)
        rows = [(name, email, kind, n, spent) for name, email, kind, n, spent in report.top]
        header = ["Customer", "Email", "Type", "Orders", "Spent"]
    elif tab == "inventory":
        stock_rows, _, _ = inventory(rng)
        rows = [
            (r.product.name, r.product.sku, r.in_stock, r.available, r.value, r.sold, r.sell_through)
            for r in stock_rows
        ]
        header = [
            "Product",
            "SKU",
            "In stock",
            "Available to sell",
            "Stock value",
            "Sold in period",
            "Sell-through %",
        ]
    elif tab == "tax":
        rows = tax(rng)
        header = [
            "Month",
            "State",
            "Orders",
            "Taxable merchandise",
            "Shipping",
            "Tax collected",
            "Tax on shipping",
        ]
    else:
        raise ValueError(tab)
    return f"bazaare-{tab}-{stamp}.csv", to_csv(header, rows)
