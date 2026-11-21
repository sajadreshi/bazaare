"""Numbers for the admin dashboard: sales, orders to ship, top sellers and catalog to-dos."""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func

from app.extension import db
from app.models import Category, Order, OrderItem, Product, User, Variant, utcnow
from app.services.catalog import category_products

ZERO = Decimal("0.00")


@dataclass
class Period:
    orders: int = 0
    revenue: Decimal = ZERO

    @property
    def average(self):
        return (self.revenue / self.orders).quantize(Decimal("0.01")) if self.orders else ZERO


@dataclass
class Dashboard:
    today: Period
    week: Period
    previous_week: Period
    to_ship: int
    daily: list  # [(date, revenue, orders)] oldest first
    recent_orders: list
    top_products: list  # [(name, sku, quantity, revenue)]
    active_products: int
    customers: int
    new_customers: int
    todos: list = field(default_factory=list)  # [(message, count, url)]

    @property
    def week_change(self):
        """Percentage change in revenue against the previous 7 days (None when there's nothing to compare)."""
        if not self.previous_week.revenue:
            return None
        return int(round((self.week.revenue - self.previous_week.revenue) / self.previous_week.revenue * 100))

    @property
    def daily_max(self):
        return max((revenue for _, revenue, _ in self.daily), default=ZERO) or Decimal(1)


def _period(orders):
    return Period(orders=len(orders), revenue=sum((o.total or ZERO for o in orders), ZERO))


def _catalog_todos():
    todos = []
    active = Product.query.filter(Product.is_active.is_(True))
    no_photo = active.filter(Product.main_image.is_(None)).count()
    if no_photo:
        todos.append(("Active products without a photo", no_photo, "/admin/product/"))
    no_category = active.filter(~Product.categories.any()).count()
    if no_category:
        todos.append(("Active products in no category (not in the menu)", no_category, "/admin/product/"))
    no_option = active.filter(~Product.variant.any(Variant.id.isnot(None))).count()
    if no_option:
        todos.append(
            ("Active products with no size/design option (can't be bought)", no_option, "/admin/product/")
        )
    menu = Category.query.filter(Category.is_active.is_(True), Category.show_in_menu.is_(True))
    empty = [c.name for c in menu if c.max_price is None and not category_products(c)]
    if empty:
        todos.append((f"Empty menu categories: {', '.join(sorted(empty))}", len(empty), "/admin/category/"))
    return todos


def build_dashboard(now=None):
    now = now or utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)
    previous_start = week_start - timedelta(days=7)
    chart_start = today_start - timedelta(days=13)

    recent = (
        Order.query.filter(Order.placed_at >= min(previous_start, chart_start), Order.status != "CANCELLED")
        .order_by(Order.placed_at)
        .all()
    )
    daily = []
    for offset in range(14):
        day = (chart_start + timedelta(days=offset)).date()
        on_day = [o for o in recent if o.placed_at.date() == day]
        daily.append((day, sum((o.total or ZERO for o in on_day), ZERO), len(on_day)))

    month_start = today_start - timedelta(days=29)
    top = (
        db.session.query(OrderItem.name, OrderItem.sku, func.count(OrderItem.id), func.sum(OrderItem.price))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.placed_at >= month_start, Order.status != "CANCELLED")
        .group_by(OrderItem.name, OrderItem.sku)
        .order_by(func.count(OrderItem.id).desc(), func.sum(OrderItem.price).desc())
        .limit(5)
        .all()
    )

    return Dashboard(
        today=_period([o for o in recent if o.placed_at >= today_start]),
        week=_period([o for o in recent if o.placed_at >= week_start]),
        previous_week=_period([o for o in recent if previous_start <= o.placed_at < week_start]),
        to_ship=Order.query.filter_by(status="PLACED").count(),
        daily=daily,
        recent_orders=Order.query.order_by(Order.placed_at.desc(), Order.id.desc()).limit(8).all(),
        top_products=top,
        active_products=Product.query.filter(Product.is_active.is_(True)).count(),
        customers=User.query.count(),
        new_customers=User.query.filter(User.created_at >= week_start).count(),
        todos=_catalog_todos(),
    )
