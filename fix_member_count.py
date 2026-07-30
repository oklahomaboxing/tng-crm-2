from __future__ import annotations

import py_compile
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()

if (ROOT / "backend" / "app" / "main.py").exists():
    BACKEND = ROOT / "backend"
elif (ROOT / "app" / "main.py").exists():
    BACKEND = ROOT
else:
    raise SystemExit(
        "Could not find backend/app/main.py or app/main.py. "
        "Run this from the tng_crm_2_0 project folder."
    )

MAIN = BACKEND / "app" / "main.py"
DASHBOARD = BACKEND / "app" / "operations" / "dashboard.py"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    shutil.copy2(
        path,
        path.with_suffix(
            path.suffix + f".before_member_fix_{STAMP}.bak"
        ),
    )


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"Start marker not found: {start_marker}")

    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"End marker not found: {end_marker}")

    return (
        text[:start]
        + replacement.rstrip()
        + "\n\n"
        + text[end:]
    )


backup(MAIN)
main_text = MAIN.read_text(encoding="utf-8")

new_customer_sync = '''@app.post("/api/clover/sync-customers")
def sync_clover_customers(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = (
        os.getenv("CLOVER_ECOMMERCE_PRIVATE_KEY")
        or os.getenv("CLOVER_API_TOKEN")
    )
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(
            status_code=500,
            detail="Clover credentials missing",
        )

    base_url = (
        "https://api.clover.com"
        if clover_env == "production"
        else "https://apisandbox.dev.clover.com"
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        (
            f"{base_url}/v3/merchants/{merchant_id}/customers"
            "?expand=emailAddresses,phoneNumbers"
            "&limit=1000"
        ),
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Clover customer sync error "
                f"{response.status_code}: {response.text}"
            ),
        )

    customers = response.json().get("elements", [])

    linked_members = 0
    marketing_created = 0
    marketing_updated = 0
    marketing_skipped = 0

    for customer in customers:
        clover_customer_id = (customer.get("id") or "").strip()
        first_name = (customer.get("firstName") or "").strip()
        last_name = (customer.get("lastName") or "").strip()

        emails = (
            customer.get("emailAddresses", {})
            .get("elements", [])
        )
        email = (
            (emails[0].get("emailAddress") or "").strip().lower()
            if emails
            else ""
        )

        phones = (
            customer.get("phoneNumbers", {})
            .get("elements", [])
        )
        phone = (
            (phones[0].get("phoneNumber") or "").strip()
            if phones
            else ""
        )

        if not first_name and not last_name and not email and not phone:
            marketing_skipped += 1
            continue

        existing_member = None

        member_query = db.query(Member).filter(
            or_(
                Member.member_type == "MEMBER",
                Member.membership_start != None,
                Member.membership_end != None,
                Member.membership_status.in_(
                    ["active", "expired", "past_due"]
                ),
            )
        )

        if clover_customer_id:
            existing_member = member_query.filter(
                Member.clover_customer_id == clover_customer_id
            ).first()

        if not existing_member and email:
            existing_member = member_query.filter(
                func.lower(Member.email) == email
            ).first()

        if not existing_member and phone:
            existing_member = member_query.filter(
                Member.phone == phone
            ).first()

        if existing_member:
            if clover_customer_id:
                existing_member.clover_customer_id = clover_customer_id
            if first_name:
                existing_member.first_name = first_name
            if last_name:
                existing_member.last_name = last_name
            if email:
                existing_member.email = email
            if phone:
                existing_member.phone = phone
            linked_members += 1

        marketing_result = sync_clover_customer_to_marketing(
            db,
            first_name,
            last_name,
            email,
            phone,
        )

        if marketing_result == "created":
            marketing_created += 1
        elif marketing_result == "updated":
            marketing_updated += 1
        else:
            marketing_skipped += 1

    db.commit()

    return {
        "message": "Clover customers synced to marketing contacts",
        "customers_received": len(customers),
        "members_linked": linked_members,
        "members_created": 0,
        "marketing": {
            "created": marketing_created,
            "updated": marketing_updated,
            "skipped": marketing_skipped,
        },
    }'''

main_text = replace_between(
    main_text,
    '@app.post("/api/clover/sync-customers")',
    '@app.post("/api/members/activate-prospects")',
    new_customer_sync,
)

members_start = main_text.find('@app.get("/api/members")')
members_end = main_text.find(
    '@app.post("/api/products")',
    members_start,
)

if members_start < 0 or members_end < 0:
    raise RuntimeError("Could not locate /api/members endpoint.")

members_block = main_text[members_start:members_end]

old_query_pattern = re.compile(
    r'''    paid_sale_member_ids = \(.*?    members = \(.*?        \.all\(\)\n    \)\n''',
    re.DOTALL,
)

new_query = '''    paid_membership_member_ids = (
        db.query(Sale.member_id)
        .join(
            MembershipProduct,
            MembershipProduct.id == Sale.product_id,
        )
        .filter(
            Sale.payment_status == "paid",
            Sale.member_id != None,
            or_(
                Sale.sale_type == "membership",
                MembershipProduct.is_membership == True,
                MembershipProduct.category == "membership",
            ),
        )
        .distinct()
        .subquery()
    )

    members = (
        db.query(Member)
        .filter(
            Member.id.in_(
                db.query(
                    paid_membership_member_ids.c.member_id
                )
            ),
            Member.member_type == "MEMBER",
        )
        .order_by(
            Member.last_name.asc(),
            Member.first_name.asc(),
        )
        .all()
    )
'''

members_block, count = old_query_pattern.subn(
    new_query,
    members_block,
    count=1,
)

if count != 1:
    raise RuntimeError(
        "Could not replace the /api/members membership query."
    )

needle = '''        recalculate_member_from_payments(member, db)

        # Exclude memberships expiring July 20, 2026 or earlier.
'''

replacement = '''        recalculate_member_from_payments(member, db)

        if member.member_type != "MEMBER":
            continue

        if member.membership_status != "active":
            continue

        # Exclude memberships expiring July 20, 2026 or earlier.
'''

if needle not in members_block:
    raise RuntimeError(
        "Could not add active-member filtering."
    )

members_block = members_block.replace(
    needle,
    replacement,
    1,
)

main_text = (
    main_text[:members_start]
    + members_block
    + main_text[members_end:]
)

MAIN.write_text(main_text, encoding="utf-8")

if DASHBOARD.exists():
    backup(DASHBOARD)
    dashboard_text = DASHBOARD.read_text(encoding="utf-8")

    paid_ids_pattern = re.compile(
        r'''    paid_member_ids = \(.*?    paid_member_ids = \[\n.*?    \]\n''',
        re.DOTALL,
    )

    dashboard_paid_ids = '''    paid_member_ids = [
        row[0]
        for row in (
            db.query(Sale.member_id)
            .join(
                MembershipProduct,
                MembershipProduct.id == Sale.product_id,
            )
            .filter(
                Sale.payment_status == "paid",
                Sale.member_id != None,
                or_(
                    Sale.sale_type == "membership",
                    MembershipProduct.is_membership == True,
                    MembershipProduct.category == "membership",
                ),
            )
            .distinct()
            .all()
        )
        if row[0] is not None
    ]
'''

    dashboard_text, dashboard_count = paid_ids_pattern.subn(
        dashboard_paid_ids,
        dashboard_text,
        count=1,
    )

    if dashboard_count != 1:
        raise RuntimeError(
            "Dashboard membership query was not found."
        )

    if "from sqlalchemy import" in dashboard_text:
        match = re.search(
            r"from sqlalchemy import ([^\n]+)",
            dashboard_text,
        )
        if match and "or_" not in match.group(1):
            old_import = match.group(0)
            dashboard_text = dashboard_text.replace(
                old_import,
                old_import + ", or_",
                1,
            )
    else:
        dashboard_text = (
            "from sqlalchemy import or_\n"
            + dashboard_text
        )

    model_import = re.search(
        r"from \.\.models import ([^\n]+)",
        dashboard_text,
    )

    if model_import and "MembershipProduct" not in model_import.group(1):
        dashboard_text = dashboard_text.replace(
            model_import.group(0),
            model_import.group(0) + ", MembershipProduct",
            1,
        )

    DASHBOARD.write_text(
        dashboard_text,
        encoding="utf-8",
    )

py_compile.compile(str(MAIN), doraise=True)

if DASHBOARD.exists():
    py_compile.compile(str(DASHBOARD), doraise=True)

print("")
print("SUCCESS: Membership counting fix installed.")
print(f"Updated: {MAIN}")

if DASHBOARD.exists():
    print(f"Updated: {DASHBOARD}")

print("")
print("New rules:")
print("- Clover directory customers go to Marketing Contacts")
print("- Existing legitimate members can still link to Clover")
print("- Only paid membership products appear in Members")
print("- Only active paid memberships count on Dashboard")
print("- Existing customer records remain stored but hidden")
print("")
print("Next commands:")
print(
    "git add backend/app/main.py "
    "backend/app/operations/dashboard.py"
)
print(
    'git commit -m '
    '"Separate Clover customers from active members"'
)
print("git push origin v3-development")
