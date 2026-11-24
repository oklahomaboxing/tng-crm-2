"""Display-only phone matches; never treat a saved number as verified identity."""
from app.models import Member,MarketingContact,SalesRep,User
from app.amateurs.directory import DirectoryContact
from app.matchmaker.models import BoxingFighter
from app.ticketing.models import TicketOrder
from app.ticketing.delivery import normalize_ticket_phone


def contact_names(db,phones):
    matches={p:{} for p in phones}
    if not matches:return {}
    def add(name,values):
        name=' '.join((name or '').split())
        if not name:return
        for value in values:
            try:phone=normalize_ticket_phone(value)
            except (ValueError,TypeError):continue
            if phone in matches:matches[phone].setdefault(name.casefold(),name)
    for name,values in db.query(DirectoryContact.name,DirectoryContact.phones).filter(DirectoryContact.kind=='person'):
        add(name,values or [])
    for model in (Member,MarketingContact):
        for first,last,phone in db.query(model.first_name,model.last_name,model.phone).filter(model.phone.isnot(None)):
            add(' '.join(x for x in (first,last) if x),[phone])
    for name,phone in db.query(BoxingFighter.legal_name,BoxingFighter.phone):add(name,[phone])
    for name,phone in db.query(TicketOrder.buyer_name,TicketOrder.buyer_phone).distinct():add(name,[phone])
    for name,phone in db.query(User.name,SalesRep.phone).join(SalesRep,SalesRep.user_id==User.id):add(name,[phone])
    clubs={p:set() for p in matches}
    for name,values in db.query(DirectoryContact.name,DirectoryContact.phones).filter_by(kind='club'):
        for value in values or []:
            try:p=normalize_ticket_phone(value)
            except (ValueError,TypeError):continue
            if p in clubs:clubs[p].add(name)
    from app.events.venue import VenueBooking
    for name,phone in db.query(VenueBooking.contact_name,VenueBooking.phone).distinct():add(name,[phone])
    result={}
    for phone,names in matches.items():
        names=sorted(names.values(),key=str.casefold)
        result[phone]={'club_names':sorted(clubs[phone]),'display_name':names[0] if len(names)==1 else 'Shared number' if names else 'Unknown contact','matched_names':names[:5],'matched_name_count':len(names),'name_match':'single' if len(names)==1 else 'shared' if names else 'unknown'}
    return result
