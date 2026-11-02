from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from app.models import MembershipProduct,SecurityLog
from app.member_portal.models import AssignedMembership,ConfiguredMembershipPlan


def assign_membership(db, member, name, rate, months, *, activate, user_id):
    from fastapi import HTTPException
    from sqlalchemy import select
    db.execute(select(type(member).id).where(type(member).id==member.id).with_for_update())
    rate=round(rate,2);name=name.strip()
    if not name:raise HTTPException(422,'Enter a membership name.')
    from app.services.memberships import is_ticket_purchase_name
    if is_ticket_purchase_name(name):raise HTTPException(422,'Event tickets are not gym memberships. Choose a gym membership plan.')
    candidates=db.query(MembershipProduct).filter(func.lower(MembershipProduct.name)==name.lower(),
        MembershipProduct.price==rate,MembershipProduct.default_membership_months==months,
        MembershipProduct.is_membership.is_(True),MembershipProduct.category=='membership',MembershipProduct.active.is_(True)).order_by(MembershipProduct.id).all()
    from app.services.memberships import membership_months
    product=next((candidate for candidate in candidates if membership_months(candidate)==months),None)
    if not product:
        product=MembershipProduct(name=name,price=rate,default_membership_months=months,category='membership',is_membership=True,active=True)
        db.add(product);db.flush()
    if not db.get(ConfiguredMembershipPlan,product.id):db.add(ConfiguredMembershipPlan(product_id=product.id))
    assignment=db.query(AssignedMembership).filter_by(member_id=member.id).first()
    if not assignment:assignment=AssignedMembership(member_id=member.id);db.add(assignment)
    assignment.product_id=product.id;assignment.rate=rate;assignment.months=months
    member.membership_type=name;member.monthly_rate=rate if months==1 else 0
    member.billing_cycle='30_day' if months==1 else f'{months}_month_prepaid'
    if activate:
        assignment.unrecorded_activation=rate>0
        now=datetime.utcnow();member.member_type='MEMBER';member.status='active';member.membership_status='active'
        member.membership_start=now
        member.membership_end=now+timedelta(days=30) if months==1 else now+relativedelta(months=months)
    db.add(SecurityLog(user_id=user_id,action='MEMBERSHIP_ASSIGNED',description=f'Assigned profile #{member.id} plan #{product.id}, rate {rate}, months {months}, activate={activate}; no payment recorded'))
    db.flush()
    return assignment


def preserve_recorded_rates(db,user_id):
    """Honor existing explicit monthly rates without guessing from purchase totals."""
    from app.models import Member
    changed=0
    for member in db.query(Member).filter_by(member_type='MEMBER').all():
        if member.billing_cycle!='30_day' or not member.monthly_rate or member.monthly_rate<=0 or not member.membership_type:continue
        if db.query(AssignedMembership).filter_by(member_id=member.id).first():continue
        if round(member.monthly_rate,2)==150:continue
        assign_membership(db,member,member.membership_type,member.monthly_rate,1,activate=False,user_id=user_id)
        changed+=1
    db.commit()
    return changed
