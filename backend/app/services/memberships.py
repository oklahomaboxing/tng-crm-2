from datetime import datetime, timedelta

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

    return any(keyword in name for keyword in event_keywords)


def apply_membership(member, product, purchase_date=None):
    if not is_membership_product(product):
        return member

    purchase_date = purchase_date or datetime.utcnow()
    product_name = (product.name or "").lower()
    product_price = round(float(product.price or 0), 2)

    is_three_month_membership = (
        product_price == 300.00
        or "3 month" in product_name
        or "3-month" in product_name
        or "three month" in product_name
    )

    if is_three_month_membership:
        membership_end = purchase_date + relativedelta(months=3)
        billing_cycle = "3_month_prepaid"
        monthly_rate = 0
        next_billing_date = None
    else:
        membership_end = purchase_date + timedelta(days=30)
        billing_cycle = "30_day"
        monthly_rate = product_price
        next_billing_date = membership_end

    member.status = "active"
    member.membership_status = "active"
    member.membership_type = product.name
    member.membership_start = purchase_date
    member.membership_end = membership_end
    member.last_payment_date = purchase_date
    member.billing_cycle = billing_cycle
    member.monthly_rate = monthly_rate
    member.next_billing_date = next_billing_date
    member.autopay_enabled = False
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
        .order_by(Sale.sale_date.desc())
        .all()
    )

    membership_sales = [
        sale
        for sale in membership_sales
        if (
            sale.product
            and is_membership_product(sale.product)
            and not is_event_product(sale.product)
        )
    ]

    if not membership_sales:
        return member

    last_sale = membership_sales[0]
    purchase_date = last_sale.sale_date or datetime.utcnow()

    apply_membership(
        member,
        last_sale.product,
        purchase_date=purchase_date,
    )

    if member.membership_end and member.membership_end < datetime.utcnow():
        member.membership_status = "inactive"
        member.billing_status = "expired"
    else:
        member.membership_status = "active"
        member.billing_status = "active"

    return member