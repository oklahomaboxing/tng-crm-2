"""Create fighter seller links atomically with ORM bout creation/assignment."""
from datetime import datetime
from sqlalchemy import event, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.matchmaker.models import BoxingBout, BoxingEvent, BoxingFighter
from .models import EventSeller
from .service import generate_public_code

INACTIVE = {'cancelled', 'canceled', 'void', 'withdrawn', 'deleted', 'completed', 'finished'}


def ensure_bout_ticket_sellers(connection, bout):
    if not bout.event_id or str(bout.status or '').lower() in INACTIVE:
        return 0
    event_status = connection.execute(select(BoxingEvent.status).where(BoxingEvent.id == bout.event_id)).first()
    if not event_status or str(event_status[0] or '').lower() in INACTIVE | {'completed','archived'}:
        return 0
    ids = {fid for fid in (bout.red_fighter_id, bout.blue_fighter_id) if fid}
    if not ids:
        return 0
    fighters = connection.execute(select(BoxingFighter.id, BoxingFighter.legal_name, BoxingFighter.email).where(BoxingFighter.id.in_(ids))).all()
    insert = pg_insert if connection.dialect.name == 'postgresql' else sqlite_insert
    created = 0
    for fighter in fighters:
        stmt = insert(EventSeller.__table__).values(event_id=bout.event_id, seller_type='fighter',
            seller_ref_id=fighter.id, display_name=fighter.legal_name or f'Fighter {fighter.id}',
            email=fighter.email or None, public_code=generate_public_code(bout.event_id,'fighter'),
            active=True, created_at=datetime.utcnow()).on_conflict_do_nothing(
                index_elements=['event_id','seller_type','seller_ref_id'])
        result = connection.execute(stmt)
        created += max(0,result.rowcount)
    # Existing codes, history, and explicit inactive settings are deliberately untouched.
    return created


def _after_insert(mapper, connection, target):
    ensure_bout_ticket_sellers(connection,target)


def _after_update(mapper, connection, target):
    state=inspect(target)
    if any(state.attrs[k].history.has_changes() for k in ('event_id','red_fighter_id','blue_fighter_id','status')):
        ensure_bout_ticket_sellers(connection,target)


def register_bout_ticket_automation():
    for name, callback in [('after_insert',_after_insert),('after_update',_after_update)]:
        if not event.contains(BoxingBout,name,callback):
            event.listen(BoxingBout,name,callback)
