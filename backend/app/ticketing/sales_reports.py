"""Paid ticket revenue, commission estimate, and printable/exportable event ledger."""
import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape
from sqlalchemy import func
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.matchmaker.models import BoxingEvent
from .models import TicketOrder, IssuedTicket, EventSeller, EventTicketType, PaperTicket, PaperTicketBatch


def money(cents):
    return f'${int(cents or 0) / 100:,.2f}'


def quantity(order):
    try:
        return sum(max(0, int(i.get('quantity', 0))) for i in json.loads(order.items_json or '[]'))
    except (ValueError, TypeError, AttributeError):
        return 0


def commission_summary(db, event_id, orders=None):
    orders = orders if orders is not None else db.query(TicketOrder).filter_by(event_id=event_id).all()
    paid = [o for o in orders if o.payment_status == 'paid']
    gross = sum(int(o.subtotal_cents or 0) for o in paid)
    amount = int((Decimal(gross) * Decimal('0.05')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    paper = db.query(PaperTicket).join(PaperTicketBatch).filter(PaperTicketBatch.event_id == event_id, PaperTicket.status.in_(['allocated', 'released', 'offline_used'])).all()
    issued_counts = dict(db.query(IssuedTicket.order_id, func.count(IssuedTicket.id)).filter_by(event_id=event_id).group_by(IssuedTicket.order_id).all())
    return {'rate_percent': 5, 'paid_ticket_gross_cents': gross, 'state_commission_cents': amount,
            'paid_orders': len(paid), 'paid_ticket_quantity': sum(quantity(o) for o in paid),
            'unpaid_orders': sum(o.payment_status in ('pending', 'failed') for o in orders),
            'unreconciled_paper_tickets': len(paper),
            'partial_refund_orders': sum(o.payment_status == 'partial_refund' for o in orders),
            'paid_orders_missing_tickets': sum(issued_counts.get(o.id, 0) != quantity(o) for o in paid),
            'basis': '5% of recorded paid ticket subtotals, before seller commissions. Fees and unpaid/refunded orders excluded. Partial refunds and unrecorded paper sales need reconciliation.'}


def report_data(db, event_id):
    event = db.get(BoxingEvent, event_id)
    if not event:
        raise HTTPException(404, 'Event not found')
    orders = db.query(TicketOrder).filter_by(event_id=event_id).order_by(TicketOrder.id).all()
    tickets = db.query(IssuedTicket).filter_by(event_id=event_id).order_by(IssuedTicket.id).all()
    sellers = {s.id:s for s in db.query(EventSeller).filter_by(event_id=event_id)}
    kinds = {t.id:t for t in db.query(EventTicketType).filter_by(event_id=event_id)}
    issued = defaultdict(list)
    for t in tickets:
        issued[t.order_id].append(t)
    summary = commission_summary(db, event_id, orders)
    rows = []
    seller_rows = defaultdict(lambda: {'orders':0,'quantity':0,'gross':0,'commission':0})
    for o in orders:
        seller = sellers.get(o.seller_id)
        name = seller.display_name if seller else 'Direct / unattributed'
        qs = quantity(o)
        items = issued[o.id]
        rows.append([o.id,o.receipt_number,name,o.buyer_name,o.payment_status,o.payment_provider or '',o.payment_id or '',
                     o.clover_checkout_id or '',qs,money(o.subtotal_cents),money(o.fee_cents),money(o.total_cents),
                     str(o.paid_at or o.created_at or ''),' | '.join(t.ticket_number for t in items),
                     ' | '.join(f'{t.ticket_number}: {t.status}' for t in items),
                     ' | '.join(sorted({kinds[t.ticket_type_id].name for t in items if t.ticket_type_id in kinds}))])
        if o.payment_status == 'paid':
            sr=seller_rows[name]
            sr['orders']+=1;sr['quantity']+=qs;sr['gross']+=int(o.subtotal_cents or 0)
            sr['commission']+=sum(t.commission_cents or 0 for t in items if t.status in ('valid','used'))
    paper = db.query(PaperTicket, PaperTicketBatch).join(PaperTicketBatch).filter(PaperTicketBatch.event_id==event_id,PaperTicket.status.in_(['allocated','released','offline_used'])).order_by(PaperTicket.id).all()
    paper_rows = [[t.ticket_number,b.id,sellers[b.seller_id].display_name if b.seller_id in sellers else 'Unknown',t.status,money(b.price_cents)] for t,b in paper]
    ledger = [[t.ticket_number,t.order_id,sellers[t.seller_id].display_name if t.seller_id in sellers else 'Direct / unattributed',kinds[t.ticket_type_id].name if t.ticket_type_id in kinds else '',t.status,money(t.price_cents),money(t.commission_cents),str(t.issued_at or ''),str(t.scanned_at or '')] for t in tickets]
    return event, summary, rows, seller_rows, paper_rows, ledger


def sections(event, summary, orders, sellers, paper, ledger):
    totals = [['Event',event.name],['Event date',str(event.event_date or '')],['Generated (UTC)',datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')],
              ['Paid orders',summary['paid_orders']],['Paid ticket quantity',summary['paid_ticket_quantity']],
              ['Recorded paid ticket gross',money(summary['paid_ticket_gross_cents'])],
              ['Oklahoma State Athletic Commission rate','5%'],['Oklahoma State Athletic Commission amount',money(summary['state_commission_cents'])],
              ['Unpaid orders (not included)',summary['unpaid_orders']],['Unreconciled paper tickets (not included)',summary['unreconciled_paper_tickets']],
              ['Partial refund orders (review)',summary['partial_refund_orders']],['Paid orders with issuance mismatch (review)',summary['paid_orders_missing_tickets']]]
    return [('Event summary',['Metric','Value'],totals),
            ('Paid sales by seller',['Seller','Paid orders','Tickets','Ticket gross','Seller commission'],[[n,s['orders'],s['quantity'],money(s['gross']),money(s['commission'])] for n,s in sorted(sellers.items())]),
            ('All order records - only PAID subtotals included in 5% calculation',['Order','Receipt','Seller','Buyer','Payment status','Provider','Payment ID','Clover checkout','Quantity','Ticket subtotal','Fees','Order total','Paid / created (UTC)','Ticket numbers','Ticket states','Ticket types'],orders),
            ('Issued ticket ledger',['Ticket','Order','Seller','Type','Status','Face value','Seller commission','Issued (UTC)','Scanned (UTC)'],ledger),
            ('Paper stock awaiting sales reconciliation - not paid revenue',['Ticket','Batch','Seller','Status','Face value'],paper)]


def export_csv(db, event_id):
    data = report_data(db,event_id)
    out=io.StringIO();writer=csv.writer(out)
    def safe(value):
        text=str(value)
        # Spreadsheet formula injection can originate in customer or seller names.
        return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
    for title,header,rows in sections(*data):
        writer.writerow([title]);writer.writerow(header)
        writer.writerows([[safe(x) for x in row] for row in rows]);writer.writerow([])
    writer.writerow(['Calculation basis',data[1]['basis']])
    return StreamingResponse(iter(['\ufeff'+out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="tng_event_{event_id}_ticket_report.csv"','Cache-Control':'private, no-store'})


def export_pdf(db, event_id):
    data=report_data(db,event_id)
    out=io.BytesIO();styles=getSampleStyleSheet()
    styles['BodyText'].fontSize=8;styles['BodyText'].leading=10
    styles['Heading1'].textColor=colors.HexColor('#c91c28')
    def para(value):
        return Paragraph(escape(str(value)),styles['BodyText'])
    story=[Paragraph('TNG PROMOTIONS - TICKET SALES',styles['Heading1']),para(data[0].name),Spacer(1,12)]
    for title,header,rows in sections(*data):
        story.extend([Paragraph(escape(title),styles['Heading2'])])
        # Full order references remain in CSV; the printable order ledger uses compact fields.
        if len(header)>10:
            indexes=[0,2,4,5,8,9,10,11,12]
            header=[header[i] for i in indexes];rows=[[r[i] for i in indexes] for r in rows]
        table=Table([[para(h) for h in header]]+[[para(c) for c in row] for row in rows],repeatRows=1,colWidths=[720/len(header)]*len(header),hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#efefef')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#c91c28')),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#fafafa')])]))
        story.extend([table,Spacer(1,12)])
    story.append(Paragraph('Order references', styles['Heading2']))
    header=['Order','Receipt','Buyer','Payment ID','Clover checkout']
    refrows=[[r[i] for i in (0,1,3,6,7)] for r in data[2]]
    refs=Table([[para(h) for h in header]]+[[para(c) for c in r] for r in refrows],repeatRows=1,colWidths=[40,140,130,190,220])
    refs.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#efefef'))]))
    story.extend([refs,Spacer(1,12)])
    story.extend([Paragraph('Calculation basis',styles['Heading2']),para(data[1]['basis']),para('Full payment references and buyer details are included in the CSV export. This report does not remit a payment to the commission.')])
    def footer(c,doc):
        c.setFont('Helvetica',8);c.drawString(36,20,f'TNG Promotions | Event {event_id} | Page {doc.page}')
    SimpleDocTemplate(out,pagesize=landscape(letter),leftMargin=36,rightMargin=36,topMargin=30,bottomMargin=36,title=f'{data[0].name} Ticket Sales').build(story,onFirstPage=footer,onLaterPages=footer)
    out.seek(0)
    return StreamingResponse(out,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="tng_event_{event_id}_master_report.pdf"','Cache-Control':'private, no-store'})
