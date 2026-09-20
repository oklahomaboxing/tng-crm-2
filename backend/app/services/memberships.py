from datetime import datetime, timedelta
import re

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import Sale


def is_membership_product(product):
    """
    Membership activation must be explicit.

    Clover/manual/custom/test products do NOT become memberships
    based only on their name or price.
    """
    if not product:
        return False

    name = (product.name or "").strip().lower()
    category = (getattr(product, "category", "") or "").strip().lower()

    blocked_words = {
        "test",
        "testing",
        "manual",
        "custom",
        "uncategorized",
        "clover sale",
    }

    if any(word in name for word in blocked_words):
        return False

    # Membership must be intentionally marked in TNG OS.
    return bool(
        getattr(product, "is_membership", False)
        and category == "membership"
    )


def is_event_product(product):
    if not product:
        return False

    if is_membership_product(product):
        return False

    name = (product.name or "").lower()

    event_keywords = [
        "ticket",
        "general admission",
        "ga",
        "ringside",
        "vip",
        "table",
        "admission",
        "event",
        "show",
        "fight",
    ]

    return any(re.search(r"\b" + re.escape(keyword) + r"\b", name) for keyword in event_keywords)


def membership_months(product):
    months = int(getattr(product, "default_membership_months", None) or 1)
    # Older products were all created with a one-month schema default.
    if months == 1:
        name = (product.name or "").lower()
        if "year" in name or "annual" in name:
            months = 12
        elif re.search(r"\b(?:3|three)[ -]*months?\b", name):
            months = 3
    return max(1, months)


def effective_membership_status(member, now=None):
    status = member.membership_status or "pending"
    if status == "active" and member.membership_end and member.membership_end < (now or datetime.utcnow()):
        return "inactive"
    return status


def apply_membership(member, product, purchase_date=None):
    if not is_membership_product(product):
        return member

    purchase_date = purchase_date or datetime.utcnow()
    product_price = round(float(product.price or 0), 2)
    months = membership_months(product)
    start = max(member.membership_end or purchase_date, purchase_date)

    if months > 1:
        membership_end = start + relativedelta(months=months)
        billing_cycle = f"{months}_month_prepaid"
        monthly_rate = 0
        next_billing_date = None
    else:
        membership_end = start + timedelta(days=30)
        billing_cycle = "30_day"
        monthly_rate = product_price
        next_billing_date = membership_end

    member.status = "active"
    member.membership_status = "active"
    member.membership_type = product.name
    member.membership_start = member.membership_start or purchase_date
    member.membership_end = membership_end
    member.last_payment_date = purchase_date
    member.billing_cycle = billing_cycle
    member.monthly_rate = monthly_rate
    member.next_billing_date = next_billing_date
    member.billing_status = "active"
    member.past_due_amount = 0

    return member


def recalculate_member_from_payments(member, db: Session):
    membership_sales = (
        db.query(Sale)
        .filter(
            Sale.member_id == member.id,
            Sale.payment_status == "paid",
        )
        .order_by(Sale.sale_date.asc(), Sale.id.asc())
        .all()
    )

    membership_sales = [
        sale
        for sale in membership_sales
        if (
            sale.product
            and not sale.refunded
            and not sale.refund_amount
            and is_membership_product(sale.product)
            and not is_event_product(sale.product)
        )
    ]

    if not membership_sales:
        return member

    # Only explicit repair actions call this rebuild. Reads never rewrite history.
    member.membership_start = None
    member.membership_end = None
    for sale in membership_sales:
        apply_membership(member, sale.product, purchase_date=sale.sale_date)

    if member.membership_end and member.membership_end < datetime.utcnow():
        member.membership_status = "inactive"
        member.billing_status = "expired"
    else:
        member.membership_status = "active"
        member.billing_status = "active"

    return member
