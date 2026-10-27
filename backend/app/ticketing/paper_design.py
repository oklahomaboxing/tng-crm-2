"""Print layouts: all admission data is rendered as text/vector, never AI text."""
import io
from datetime import date
from pathlib import Path
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

RED=HexColor('#D71920')
INK=HexColor('#101114')
MUTED=HexColor('#ACADB3')
ASSETS=Path(__file__).with_name('assets')
LOGO=ASSETS/'tng-logo.jpg'
pdfmetrics.registerFont(TTFont('TNG-Regular',str(ASSETS/'DejaVuSansCondensed.ttf')))
pdfmetrics.registerFont(TTFont('TNG-Bold',str(ASSETS/'DejaVuSansCondensed-Bold.ttf')))


def text(pdf,value,x,y,width,size=10,font='TNG-Regular',color=white,min_size=7):
    value=' '.join(str(value or '').split())
    while size>min_size and pdf.stringWidth(value,font,size)>width:
        size-=.5
    while pdf.stringWidth(value,font,size)>width and len(value)>3:
        value=value[:-4]+'...'
    pdf.setFillColor(color);pdf.setFont(font,size);pdf.drawString(x,y,value)


def wrap(pdf,value,width,size,font='TNG-Bold',lines=2):
    words=str(value or '').split();result=[];current=''
    for word in words:
        candidate=(current+' '+word).strip()
        if current and pdf.stringWidth(candidate,font,size)>width:
            result.append(current);current=word
        else:current=candidate
    if current:result.append(current)
    if len(result)>lines:result=result[:lines-1]+[' '.join(result[lines-1:])]
    return result


def display_date(value):
    try:
        d=date.fromisoformat(str(value)[:10])
        return d.strftime('%A, %B ')+str(d.day)+d.strftime(', %Y')
    except (TypeError,ValueError):return str(value or 'Date to be announced')


def qr_image(raw):
    qr=qrcode.QRCode(box_size=8,border=4,error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(raw);qr.make(fit=True)
    return ImageReader(qr.make_image(fill_color='black',back_color='white').convert('RGB'))


def trim(pdf,x,y,w,h):
    pdf.setStrokeColor(HexColor('#888888'));pdf.setLineWidth(.4);pdf.setDash(2,3)
    pdf.rect(x-2,y-2,w+4,h+4);pdf.setDash()


def landscape(pdf,item,event,seller,kind,price,schedule,x,y,w,h,sample):
    stub=146;body=w-stub;short=h<200
    pdf.setFillColor(INK);pdf.rect(x,y,body,h,fill=1,stroke=0)
    # Restrained boxing-ring ropes and angular red corner, all crisp in print.
    pdf.setStrokeColor(HexColor('#202126'));pdf.setLineWidth(1)
    for offset in [0,14,28]:pdf.line(x+190,y+30+offset,x+body,y+100+offset)
    pdf.setFillColor(HexColor('#791117'))
    path=pdf.beginPath();path.moveTo(x+body-35,y+h);path.lineTo(x+body,y+h);path.lineTo(x+body,y+110);path.close();pdf.drawPath(path,fill=1,stroke=0)
    pdf.drawImage(str(LOGO),x+16,y+h-(47 if short else 65),width=95 if short else 124,height=42 if short else 55,preserveAspectRatio=True,mask='auto')
    text(pdf,'OFFICIAL EVENT ADMISSION',x+(125 if short else 158),y+h-(22 if short else 27),body-(142 if short else 175),9,'TNG-Bold')
    text(pdf,'TNG BOXING PRESENTS',x+(125 if short else 158),y+h-(36 if short else 43),body-(142 if short else 175),8,'TNG-Bold',RED)
    title=str(event.name or 'Boxing event').upper()
    for i,line in enumerate(wrap(pdf,title,body-36,21 if short else 25)):
        text(pdf,line,x+18,y+h-(65 if short else 92)-i*(20 if short else 26),body-36,21 if short else 25,'TNG-Bold',min_size=14)
    text(pdf,display_date(event.event_date),x+18,y+(73 if short else 91),body-36,11 if short else 12,'TNG-Bold')
    text(pdf,event.venue or 'Venue to be announced',x+18,y+(59 if short else 73),body-36,10 if short else 11,'TNG-Bold')
    for i,line in enumerate(wrap(pdf,event.venue_address,body-36,8,'TNG-Regular',1 if short else 2)):
        text(pdf,line,x+18,y+(46 if short else 59)-i*10,body-36,8,color=MUTED)
    text(pdf,schedule or 'Event schedule: see official event updates',x+18,y+(33 if short else 35),body-36,7 if short else 8,color=MUTED)
    pdf.setFillColor(RED);pdf.rect(x,y,body,27,fill=1,stroke=0)
    text(pdf,kind.upper(),x+18,y+9,body-110,12,'TNG-Bold')
    text(pdf,f'${price/100:,.2f}',x+body-92,y+8,78,15,'TNG-Bold')
    sx=x+body
    pdf.setFillColor(HexColor('#F7F7F4'));pdf.rect(sx,y,stub,h,fill=1,stroke=0)
    pdf.setFillColor(RED);pdf.rect(sx,y+h-31,stub,31,fill=1,stroke=0)
    text(pdf,'SAMPLE / NOT VALID' if sample else 'EVENT PASS',sx+15,y+h-21,stub-24,11,'TNG-Bold')
    pdf.drawImage(qr_image(item['raw']),sx+(25 if short else 17),y+(49 if short else 76),width=96 if short else 112,height=96 if short else 112)
    text(pdf,item['number'],sx+12,y+(39 if short else 63),stub-24,8 if short else 9,'TNG-Bold',black)
    if not short:text(pdf,'SOLD THROUGH',sx+12,y+46,stub-24,7,'TNG-Bold',HexColor('#666666'))
    text(pdf,seller,sx+12,y+(25 if short else 32),stub-24,9 if short else 10,'TNG-Bold',black)
    status='ACTIVATE AFTER SALE' if item.get('status')=='allocated' else 'PRESENT AT CHECK-IN'
    text(pdf,'NOT VALID FOR ENTRY' if sample else status,sx+12,y+12,stub-24,7,'TNG-Bold',RED)
    pdf.setStrokeColor(HexColor('#AAAAB0'));pdf.setDash(3,3);pdf.line(sx,y,sx,y+h);pdf.setDash()
    if sample:
        pdf.saveState();pdf.translate(x+24,y+(83 if short else 104));pdf.rotate(10)
        pdf.setFillColor(RED);pdf.setFillAlpha(.22);pdf.setFont('TNG-Bold',32);pdf.drawString(0,0,'DESIGN PREVIEW');pdf.restoreState()
    trim(pdf,x,y,w,h)


def compact(pdf,item,event,seller,kind,price,schedule,x,y,w,h,sample):
    pdf.setFillColor(white);pdf.rect(x,y,w,h,fill=1,stroke=0)
    pdf.setFillColor(INK);pdf.rect(x,y+h-60,w,60,fill=1,stroke=0)
    pdf.drawImage(str(LOGO),x+10,y+h-53,width=102,height=45,preserveAspectRatio=True)
    text(pdf,'TNG BOXING',x+124,y+h-25,w-136,10,'TNG-Bold')
    text(pdf,'EVENT ADMISSION',x+124,y+h-41,w-136,7,'TNG-Bold',RED)
    for i,line in enumerate(wrap(pdf,str(event.name).upper(),w-24,15)):
        text(pdf,line,x+12,y+h-79-i*17,w-24,15,'TNG-Bold',black)
    text(pdf,schedule,x+12,y+129,w-24,7,color=HexColor('#555555'))
    text(pdf,display_date(event.event_date),x+12,y+116,w-24,9,'TNG-Bold',black)
    text(pdf,event.venue or 'Venue to be announced',x+12,y+103,w-24,9,color=black)
    text(pdf,event.venue_address,x+12,y+91,w-24,7,color=HexColor('#555555'))
    pdf.drawImage(qr_image(item['raw']),x+9,y+9,width=78,height=78)
    text(pdf,kind,x+96,y+73,w-108,10,'TNG-Bold',black)
    text(pdf,f'${price/100:,.2f}',x+96,y+56,w-108,14,'TNG-Bold',RED)
    text(pdf,seller,x+96,y+41,w-108,8,color=black)
    text(pdf,item['number'],x+96,y+26,w-108,8,'TNG-Bold',black)
    label='SAMPLE / NOT VALID' if sample else ('ACTIVATE AFTER SALE' if item.get('status')=='allocated' else 'PRESENT AT CHECK-IN')
    text(pdf,label,x+96,y+12,w-108,7,'TNG-Bold',RED)
    trim(pdf,x,y,w,h)


def render_tickets(event,seller,kind,price,items,layout='fight-night',schedule='',sample=False,batch_id=None):
    output=io.BytesIO();pdf=canvas.Canvas(output,pagesize=letter,pageCompression=1)
    pdf.setTitle(('SAMPLE - ' if sample else '')+f'TNG Boxing | {event.name} | Paper tickets')
    pdf.setAuthor('TNG Boxing')
    per_page=4 if layout=='fight-night' else 6
    for index,item in enumerate(items):
        if index and index%per_page==0:pdf.showPage()
        if index%per_page==0:
            text(pdf,'TNG BOXING / '+('DESIGN PREVIEW - NOT VALID FOR ENTRY' if sample else f'PAPER TICKETS / BATCH {batch_id}'),24,779,564,7,'TNG-Bold',black)
            text(pdf,'US LETTER / ACTUAL SIZE 100% / CUT ON DASHED LINES / REPRINTS REUSE THE SAME QR',24,12,564,6,color=black)
        if layout=='fight-night':landscape(pdf,item,event,seller,kind,price,schedule,24,591-(index%4)*189,564,177,sample)
        else:compact(pdf,item,event,seller,kind,price,schedule,24+(index%2)*282,524-((index%6)//2)*246,276,238,sample)
    pdf.save();return output.getvalue()
