"""Retry persisted notification failures without changing payments or issuing tickets."""
import asyncio
import logging
from datetime import datetime
from sqlalchemy import or_
from app.database import SessionLocal
from .models import TicketDelivery, TicketOrder
from .delivery import deliver_order


def retry_deliveries():
    with SessionLocal() as db:
        orders = db.query(TicketDelivery.order_id).filter(
            TicketDelivery.status.in_(["pending", "failed"]), TicketDelivery.attempts < 8,
            or_(TicketDelivery.next_attempt_at == None, TicketDelivery.next_attempt_at <= datetime.utcnow())
        ).distinct().limit(25).all()
        for (order_id,) in orders:
            order = db.query(TicketOrder).filter_by(id=order_id, payment_status="paid").first()
            if order:
                try:
                    deliver_order(db, order, force=False)
                except Exception:
                    db.rollback()
                    logging.getLogger(__name__).exception("Ticket delivery retry failed for order %s", order_id)


async def delivery_loop():
    while True:
        try:
            await asyncio.to_thread(retry_deliveries)
        except Exception:
            logging.getLogger(__name__).exception("Ticket delivery worker failed")
        await asyncio.sleep(30)
