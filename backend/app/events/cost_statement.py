"""Cost-only partner statement. No buyer details or individual fighter agreements."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle

def statement(d):
 s=d['summary'];expenses=[e for e in d['expenses'] if e['treatment'] in ('other','state_assessment')]
 rows=[{'name':'Purses & allowances (both corners)','cost_cents':s['purse_cost_cents'],'recorded_paid_cents':s['purse_payments_recorded_cents']},
       {'name':'Ticket commissions','cost_cents':s['commission_cost_cents'],'recorded_paid_cents':s['commission_payments_recorded_cents']},
       {'name':'State assessment','cost_cents':s['state_assessment_cents'],'recorded_paid_cents':sum(e['actual_cents'] or 0 for e in expenses if e['treatment']=='state_assessment' and e['paid'])},
       {'name':'Operating expenses','cost_cents':s['other_expenses_cents'],'recorded_paid_cents':sum(e['actual_cents'] or 0 for e in expenses if e['treatment']=='other' and e['paid'])}]
 paid=sum(r['recorded_paid_cents'] for r in rows)
 return {'event':d['event'],'categories':rows,'expenses':[{'name':e['name'],'actual_cents':e['actual_cents'],'marked_paid':bool(e['paid']),'category':e['treatment']} for e in expenses],
 'total_cost_cents':s['total_cost_cents'],'recorded_paid_cents':paid,'unpaid_or_unrecorded_cents':max(0,s['total_cost_cents']-paid),'provisional':d['provisional'],
 'basis':'Costs include obligations. Recorded payments and marked-paid entries are not bank verification. The remaining amount is unpaid or payment is not yet recorded. Excluded placeholders and duplicate purse/commission expense entries are omitted. No allocation of a specific sponsorship payment to a bill is implied.'}

def pdf(d):
 out=BytesIO();styles=getSampleStyleSheet();money=lambda v:'Not recorded' if v is None else f'${v/100:,.2f}'
 story=[Paragraph(escape(d['event']['name'])+' — Event cost statement',styles['Title']),Paragraph(escape(d['basis']),styles['BodyText']),Spacer(1,18)]
 data=[['Cost category','Obligation','Recorded paid']]+[[r['name'],money(r['cost_cents']),money(r['recorded_paid_cents'])] for r in d['categories']]+[['TOTAL',money(d['total_cost_cents']),money(d['recorded_paid_cents'])]]
 data2=[['Expense entry','Amount','Payment status']]+[[Paragraph(escape(e['name']),styles['BodyText']),money(e['actual_cents']),'Marked paid' if e['marked_paid'] else 'Not recorded paid'] for e in d['expenses']]
 for rows in [data,data2]:
  table=Table(rows,colWidths=[270,105,125],repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#142337')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d9dee5')),('FONTSIZE',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9)]));story.extend([table,Spacer(1,18)])
 SimpleDocTemplate(out,pagesize=letter,leftMargin=36,rightMargin=36).build(story);return out.getvalue()
