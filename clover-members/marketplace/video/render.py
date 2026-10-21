from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import textwrap,subprocess
root=Path(__file__).parent
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def f(n):return ImageFont.truetype(font,n)
slides=[
('TNG Members on Clover','Member profiles and check-in','Private test version 0.2.0\nStation Duo merchant + customer screens','Illustrated workflow overview. Not a device recording.'),
('01  Staff sign-in','Your gym, on Clover.','Staff email\nPassword\nSign in to TNG Members','Staff use their authorized TNGOS account on the merchant screen.'),
('02  Find a member','Members','Search by name or member number\n\nAlex Example     #1042\nMembership: Active','Synthetic example. Profiles are read from TNGOS, not Clover Customers.'),
('03  Review the profile','Alex Example  |  #1042','Membership status and expiration\nWaiver-on-file status\nRecent check-in history\nBasic contact details','Authorized staff can edit contact details. Billing eligibility is not edited here.'),
('04  Open the customer screen','Customer check-in','Merchant display: staff controls\n\nCustomer display: member keypad\nand QR scan request','Staff select “Open customer check-in screen” while Clover is idle.'),
('05  Member number check-in','MEMBER CHECK-IN','Member number: 1042\n\n1  2  3     4  5  6     7  8  9\n\nCheck me in','The customer enters a member number and submits it for validation.'),
('06  QR check-in alternative','Scan my QR card','Customer requests a scan\nClover scanner reads the QR\nTNGOS checks membership eligibility','QR scanning and both-display operation still require physical-device testing.'),
('07  Results and next member','Welcome, Alex!','Eligible: check-in recorded\nNot eligible or unknown: see staff\n\nCustomer screen resets for the next member','Success is shown only after the backend confirms the check-in.'),
('08  Data access and availability','Designed for front-desk use','Reads: member profiles and attendance\nWrites: contact updates and check-ins\nNo Clover customer/order/payment data\nInternet required; no offline check-in queue','Support: marketing@tngboxinggym.com  |  405-959-5823'),
('Before production use','Complete Station Duo testing','Install through an authorized Clover route\nVerify both displays and QR scanning\nTest eligible and ineligible members\nConfirm repeat check-ins and staff sign-out','This video explains the implemented workflow; it does not prove hardware operation.')]
for i,(title,screen,body,caption) in enumerate(slides):
 im=Image.new('RGB',(1280,720),'#0f0f16');d=ImageDraw.Draw(im)
 d.text((48,25),'TNG BOXING  /  TNG MEMBERS',font=f(18),fill='#b8b8c8')
 d.text((48,65),title,font=f(38),fill='white')
 d.rounded_rectangle((48,132,1232,551),radius=20,fill='#20212d',outline='#424456',width=2)
 d.text((80,157),screen,font=f(30),fill='#70e4b0')
 y=218
 for line in body.split('\n'):
  for part in textwrap.wrap(line,66) or ['']:
   d.text((80,y),part,font=f(26),fill='white');y+=43
 y=575
 for line in textwrap.wrap(caption,89):d.text((48,y),line,font=f(23),fill='#d2d2df');y+=32
 d.text((48,677),'ILLUSTRATED WALKTHROUGH  •  Synthetic data  •  Not a live device recording',font=f(16),fill='#a6a6bb')
 d.text((1140,677),f'{i+1} / {len(slides)}',font=f(16),fill='#a6a6bb')
 im.save(root/f'slide{i:02}.png')
(root/'slides.txt').write_text(''.join(f"file '{root}/slide{i:02}.png'\nduration 7\n" for i in range(len(slides)))+f"file '{root}/slide{len(slides)-1:02}.png'\n")
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(root/'slides.txt'),'-vf','fps=24','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'TNG-Members-Functional-Walkthrough.mp4')],check=True)
print('Video created:',(root/'TNG-Members-Functional-Walkthrough.mp4').stat().st_size,'bytes')
