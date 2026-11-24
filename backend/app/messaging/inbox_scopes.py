"""Separate work contacts by normalized phone, without splitting or copying SMS history."""
from app.amateurs.directory import DirectoryContact
from app.ticketing.delivery import normalize_ticket_phone

def official_phones(db):
    phones=set()
    for c in db.query(DirectoryContact).filter_by(kind='person'):
        if 'official' not in (c.details or {}).get('categories',[]) and not(c.role_verified and c.roles):continue
        for raw in c.phones or []:
            try:p=normalize_ticket_phone(raw)
            except (ValueError,TypeError):continue
            if p:phones.add(p)
    return phones

def club_phones(db):
    phones=set()
    for c in db.query(DirectoryContact).filter_by(kind='club'):
        if str((c.details or {}).get('state','')).strip().casefold()not in {'ok','oklahoma'}:continue
        for raw in c.phones or []:
            try:p=normalize_ticket_phone(raw)
            except (ValueError,TypeError):continue
            if p:phones.add(p)
    return phones

def scoped(query,column,scope,officials,clubs=None):
    if scope=='clubs':return query.filter(column.in_(clubs or set()))
    if scope=='officials':return query.filter(column.in_(officials))
    if scope=='gym':return query.filter(~column.in_(officials))
    return query
