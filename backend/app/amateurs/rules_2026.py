"""2026 rulebook page 53 (chart labelled revised 1/1/25), Rule 9 and Appendix H.

Transcribed from the user-supplied official PDF and visually checked. Local matched
bouts only: this is not the advancing-national-tournament classification system.
"""
import calendar
from datetime import date
DOCUMENT_SHA256='39c1d0c67b266cacb3341b2bcc23842da4d5ca6c57fc59eccb60380333faa28a'
IMPLEMENTATION='usab_appendix_f_2026_local_v1'
TITLE='2026 USA Boxing rulebook · Appendix F local matched bouts'
AGE_RANGES={8:(8,9),9:(8,11),10:(9,12),11:(9,13),12:(10,14),13:(11,15),14:(12,16),15:(13,17),16:(14,17),17:(15,18),18:(17,40)}
PREP_WEIGHTS=[(101,5),(106,7),(110,7),(114,7),(119,7),(125,9),(132,9),(138,9),(145,9),(154,9),(float('inf'),12)]
JUNIOR_WEIGHTS=PREP_WEIGHTS[:-1]+[(165,12),(176,12),(float('inf'),None)]
MEN_WEIGHTS=[(110,6),(121,8),(132,8),(143,10),(154,10),(165,15),(176,15),(187,15),(198,15),(float('inf'),None)]
WOMEN_WEIGHTS=[(106,8),(112,8),(119,8),(125,8),(132,10),(143,10),(154,10),(165,15),(176,15),(float('inf'),None)]
APPENDIX_TRANSCRIPT='''2026 USA Boxing National Rulebook, Appendix F, page 53. Local matched ages by date of birth: 8:8–9; 9:8–11; 10:9–12; 11:9–13; 12:10–14; 13:11–15; 14:12–16; 15:13–17; 16:14–17; 17:15–18; 18:17–40; Elite 19–40 may box 18–40. Maximum 24-month age difference for boxers 8–17. Masters 35+ may box only other Masters within 10 years. Rule 9.1 requires lower-age-division competition rules, consideration of total bouts and winning percentages, both coaches' discretion and final Official in Charge approval. Coed local bouts permitted at ages 8–10. Appendix H requires registered Masters classification for 35–40. Weight differentials transcribed in rules_2026.py; apply the lower-age division and each boxer's applicable weight tolerance conservatively. No unlimited-class weight gap is invented as an official rule. No universal experience-gap limit is stated; TNG preferences are separate.'''

def age_at(dob,day):return day.year-dob.year-int((day.month,day.day)<(dob.month,dob.day))
def within_month_gap(a,b,months):
    older,younger=sorted([a,b]);m=older.year*12+older.month-1+months;y,m0=divmod(m,12)
    return younger<=date(y,m0+1,min(older.day,calendar.monthrange(y,m0+1)[1]))
def age_allows(age,other):return AGE_RANGES[age][0]<=other<=AGE_RANGES[age][1] if age in AGE_RANGES else 18<=other<=40 if 19<=age<=40 else False

def classifications(data,age):
    if age>=41:return {'masters'}
    if age>=35:
        status=data.get('masters_class','')
        return {'elite','masters'} if status=='both' else {status} if status in ('elite','masters') else set()
    return {'elite'} if age>=18 else {'junior'}

def weight_limit(weight,table):return next(gap for top,gap in table if weight<=top)
def compatible(a,b,day,prefs):
    da,db=date.fromisoformat(a['dob']),date.fromisoformat(b['dob']);aa,ab=age_at(da,day),age_at(db,day)
    if min(aa,ab)<8:return None
    ca,cb=classifications(a,aa),classifications(b,ab)
    if not ca or not cb:return None
    masters='masters' in ca and 'masters' in cb
    if masters:
        if min(aa,ab)<35 or not within_month_gap(da,db,120):return None
    elif aa>=41 or ab>=41 or not age_allows(aa,ab) or not age_allows(ab,aa) or ('masters' in ca and 'elite' not in ca) or ('masters' in cb and 'elite' not in cb):return None
    if not masters and min(aa,ab)<=17 and not within_month_gap(da,db,24):return None
    coed=a['sex']!=b['sex']
    if coed and not (prefs['allow_coed_peewee'] and 8<=aa<=10 and 8<=ab<=10):return None
    if not prefs['allow_same_club'] and ''.join(a['club'].casefold().split())==''.join(b['club'].casefold().split()):return None
    if abs(a['bouts']-b['bouts'])>prefs['max_bout_gap']:return None
    lower=min(aa,ab)
    table=(MEN_WEIGHTS if a['sex']=='MALE' else WOMEN_WEIGHTS) if masters or lower>=17 else JUNIOR_WEIGHTS if lower>=15 else PREP_WEIGHTS
    la,lb=weight_limit(a['weight_lb'],table),weight_limit(b['weight_lb'],table)
    gap=abs(a['weight_lb']-b['weight_lb'])
    if any(limit is not None and gap>limit+1e-8 for limit in (la,lb)):return None
    if la is None and lb is None and gap>prefs['max_unlimited_weight_gap_lb']+1e-8:return None
    division='Masters' if masters else 'Pee Wee' if lower<=10 else 'Bantam' if lower<=12 else 'Intermediate' if lower<=14 else 'Junior' if lower<=16 else 'Youth' if lower<=18 else 'Elite'
    max_minutes=2 if masters else 1.5 if lower<=12 else 2 if lower<=16 else 3
    missing_wins=a.get('wins') is None or b.get('wins') is None
    return {'division':division,'reference':'2026 rulebook Appendix F p.53; Rule 9.1'+('; Appendix H' if masters else ''),'rounds':3,'max_round_minutes':max_minutes,'coed':coed,'masters':masters,'age_basis':'birthday','weight_limits_lb':[la,lb],'experience_review_required':True,'winning_percentages_missing':missing_wins,'win_percentages':[round(x['wins']/x['bouts']*100,1) if x.get('wins') is not None and x['bouts'] else None for x in (a,b)]}
