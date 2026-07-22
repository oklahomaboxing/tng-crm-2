from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.database import get_db
from app.models import MembershipProduct, User


router = APIRouter(
    prefix="/api/products",
    tags=["Operations - Products"],
)


@router.get("")
def list_products(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return (
        db.query(MembershipProduct)
        .order_by(MembershipProduct.name.asc())
        .all()
    )


@router.put("/{product_id}")
def update_product(
    product_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    product = (
        db.query(MembershipProduct)
        .filter(MembershipProduct.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    allowed_fields = [
        "name",
        "price",
        "active",
        "category",
        "is_membership",
        "renews_monthly",
        "autopay_allowed",
        "default_membership_months",
        "sku",
        "stock_quantity",
        "track_inventory",
    ]

    for field in allowed_fields:
        if field in data:
            setattr(product, field, data[field])

    if "category" in data:
        product.category = (
            data["category"] or "other"
        ).strip().lower()

        product.is_membership = (
            product.category == "membership"
        )

    elif "is_membership" in data:
        product.is_membership = bool(
            data["is_membership"]
        )

        if product.is_membership:
            product.category = "membership"

        elif product.category == "membership":
            product.category = "other"

    db.commit()
    db.refresh(product)

    return {
        "message": "Product updated",
        "product": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "active": product.active,
            "category": product.category,
            "is_membership": product.is_membership,
            "renews_monthly": product.renews_monthly,
            "autopay_allowed": product.autopay_allowed,
            "default_membership_months": product.default_membership_months,
            "sku": product.sku,
            "stock_quantity": product.stock_quantity,
            "track_inventory": product.track_inventory,
        },
    }