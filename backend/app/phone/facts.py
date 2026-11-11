"""Live public facts. Never reads negotiated member rates or private bout contracts."""
import re
from datetime import date,datetime
from decimal import Decimal
from sqlalchemy import func
from app.services.public_membership_catalog import public_join_products,public_registration_fee
from app.services.business_time import reporting_periods
from app.matchmaker.models import BoxingEvent,BoxingEventPublication
from app.ticketing.models import EventTicketType,EventSeller
from app.ticketing.sales_access import sales_access


def dollars(value):
    number=Decimal(str(value)).quantize(Decimal('.01'))
    return f'{int(number)} dollars' if number==int(number) else f'{number:.2f} dollars'


def membership_answer(db,fallback):
    products=public_join_products(db)
    if not products:return fallback
    def priority(p):
        name=p.name.strip().casefold()
        return (name not in ('month to month','monthly membership'),name in ('membership','monthly'),len(name))
    groups={}
    for p in sorted(products,key=priority):groups.setdefault(p.price,p)
    phrases=[]
    for price,p in sorted(groups.items()):
        name=p.name.strip()
        if re.search(r'\$\s*\d',name):phrases.append(re.sub(r'\$\s*(\d+(?:\.\d+)?)',lambda m:dollars(m.group(1)),name))
        else:phrases.append(f'{name} is {dollars(price)}')
    answer='Our current public signup plans include: '+'. '.join(phrases[:5])+'. '
    fee=public_registration_fee(db)
    if fee and fee.price>0:answer+=f'New signups also have a {dollars(fee.price)} registration fee. '
    answer+='Staff can confirm which plan and terms apply to you. To sign up now and receive the registration and waiver link, press 7. To request a visit or callback, press 4.'
    return answer


def public_events(db):
    today=reporting_periods()['local_day']
    rows=db.query(BoxingEvent,BoxingEventPublication).join(BoxingEventPublication,BoxingEventPublication.event_id==BoxingEvent.id).filter(BoxingEventPublication.published==True,BoxingEvent.event_date>=today).order_by(BoxingEvent.event_date.asc()).all()
    result=[]
    for event,pub in rows:
        if (event.status or '').lower() in ('cancelled','canceled','void','archived'):continue
        try:date.fromisoformat(event.event_date)
        except ValueError:continue
        result.append((event,pub))
    return result


def clock(value):
    try:return datetime.strptime(value,'%H:%M').strftime('%I:%M %p').lstrip('0')
    except ValueError:return value or ''


def event_answer(db,fallback):
    events=public_events(db)
    if not events:return fallback
    event,pub=events[0]
    day=date.fromisoformat(event.event_date).strftime('%A, %B %d, %Y')
    answer=f'Our next published event is {pub.public_title or event.name}, on {day}. '
    if event.venue:answer+=f'The venue is {event.venue}. '
    if event.venue_address:answer+=f'{event.venue_address}. '
    if pub.doors_time:answer+=f'Doors open at {clock(pub.doors_time)}. '
    if pub.first_bout_time:answer+=f'The first bout starts at {clock(pub.first_bout_time)}. '
    answer+='Times are Oklahoma local time. For a secure ticket checkout link, say buy tickets or press 5.'
    return answer


def ticket_events(db):
    result=[]
    for event,pub in public_events(db):
        if not db.query(EventTicketType.id).filter_by(event_id=event.id,active=True).first():continue
        company=db.query(EventSeller).filter(EventSeller.event_id==event.id,func.lower(func.trim(EventSeller.display_name))=='tng promotions',EventSeller.seller_type!='fighter').all()
        seller=next((s for s in company if sales_access(db,event.id,s)['sales_open']),None)
        if company and not seller:continue
        if sales_access(db,event.id,seller)['sales_open']:result.append((event,pub,seller))
    return result[:9]
