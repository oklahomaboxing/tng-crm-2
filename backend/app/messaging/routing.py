"""One folder per SMS conversation, with explicit staff routing taking precedence."""
from datetime import datetime
from sqlalchemy import Column,String,DateTime
from app.database import Base
from app.ticketing.delivery import normalize_ticket_phone
from .inbox_scopes import official_phones,club_phones

FOLDERS=('gym','officials','clubs','venue')
class InboxConversation(Base):
    __tablename__='sms_inbox_conversations'
    phone=Column(String(40),primary_key=True)
    folder=Column(String(20),nullable=False)
    updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def venue_phones(db):
    from app.events.venue import VenueBooking
    phones=set()
    for raw, in db.query(VenueBooking.phone).distinct():
        try:p=normalize_ticket_phone(raw)
        except (ValueError,TypeError):continue
        if p:phones.add(p)
    return phones

def folders(db,phones):
    phones=set(phones)
    if not phones:return {}
    officials=official_phones(db);clubs=club_phones(db);venue=venue_phones(db)
    result={p:('venue' if p in venue else 'officials' if p in officials else 'clubs' if p in clubs else 'gym')for p in phones}
    for row in db.query(InboxConversation).filter(InboxConversation.phone.in_(phones)):
        if row.folder in FOLDERS:result[row.phone]=row.folder
    return result
