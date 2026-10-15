"""Public promoter profiles, fetched without an AI provider or licensed feed."""
import html
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urljoin
import requests
from fastapi import HTTPException
from .discovery import STATES, public_url

SOURCES = [
 ('https://toprank.com/sitemap.xml',r'<loc>(https://(?:www\.)?toprank.com/fighters/[^<]+)</loc>'),
 ('https://www.goldenboy.com/fighters/',r'href=["\x27](https://www.goldenboy.com/fighter-profile/[^"\x27]+)'),
 ('https://www.matchroomboxing.com/boxers/',r'href=["\x27](https://www.matchroomboxing.com/boxers/[^"\x27]+)'),
]
_cache = None
_cache_at = 0
_lock = threading.Lock()
PUBLISHERS={'toprank.com','goldenboy.com','matchroomboxing.com','redowlboxing.com'}


def get_public_page(url,timeout=10):
    """Allow canonical www/slash redirects only within the same publisher."""
    publisher=(urlsplit(url).hostname or '').removeprefix('www.')
    if publisher not in PUBLISHERS:return None
    for _ in range(4):
        if not public_url(url) or (urlsplit(url).hostname or '').removeprefix('www.')!=publisher:return None
        response=requests.get(url,timeout=timeout,allow_redirects=False)
        if response.status_code not in (301,302,303,307,308):return response
        url=urljoin(url,response.headers.get('Location',''))
    return None


def plain(raw):
    return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',raw,flags=re.S)))).strip()


def parse_profile(url, raw):
    title=re.search(r'<title>(.*?)</title>',raw,re.S)
    if not title:return None
    name=re.split(r'\s+(?:\||-\s+Golden Boy|-\s+Matchroom)',plain(title.group(1)))[0].strip()
    text=plain(raw)
    start=text.find(name,text.find(name)+len(name))
    if start<0:start=text.find(name)
    profile=text[max(0,start):]
    if not name or len(name)>180:return None
    weight=record=contact=activity=''
    host=urlsplit(url).hostname
    if host in ('toprank.com','www.toprank.com'):
        h=re.search(r'Hometown (.*?) Country ',profile)
        if not h:return None
        hometown=h.group(1)
        m=re.search(r'([^\d]{2,45}?\(\d+ lbs\))',profile[len(name):len(name)+65])
        if m:weight=m.group(1).strip()
        m=re.search(r'(\d+) Wins (\d+) Losses (\d+) Draws',profile)
        if m:record='-'.join(m.groups())+' (promoter profile; verify current record)'
        m=re.search(r'Fight history.*? (\w{3} \d{1,2}, \d{4})',profile)
        if m:activity='Profile lists bout '+m.group(1)+'; current status to verify'
        promoter='Top Rank'
    elif host=='www.goldenboy.com':
        h=re.search(r'HOMETOWN:\s*(.*?)(?: BIOGRAPHY| FIGHTS| MEDIA)',profile)
        if not h:return None
        hometown=h.group(1)
        m=re.search(r'Weight Class Stance Age Height (.*?) NATIONALITY:',profile)
        if m:
            # Only the weight label, not age/height numbers or zero placeholders.
            w=re.match(r'([A-Za-z -]+?)(?: Orthodox| Southpaw| Switch| \d)',m.group(1))
            if w:weight=w.group(1).strip()
        counters=dict((label,int(value)) for value,label in re.findall(r'data-purecounter-end=["\x27](\d+)["\x27][^>]*>.*?</h\d>\s*<p[^>]*>\s*(WINS|LOSSES|DRAWS)\s*</p>',raw,re.S))
        if all(k in counters for k in ('WINS','LOSSES','DRAWS')) and sum(counters.values())>0:
            record='-'.join(str(counters[k]) for k in ('WINS','LOSSES','DRAWS'))+' (promoter profile; verify current record)'
        contact='(213) 489-5631' if '(213) 489-5631' in text else ''
        promoter='Golden Boy Promotions'
    elif host=='www.matchroomboxing.com':
        h=re.search(r'Hometown (.*?) (?:KO|Age|Stance|L \d)',profile)
        if not h:return None
        hometown=h.group(1)
        m=re.search(r'^(.*?) W (\d+)',profile[len(name):profile.find('Hometown')].strip())
        if m:weight=m.group(1).strip()
        stats=[re.search(r'\b'+x+r' (\d+)\b',profile[:700]) for x in ('W','L','D')]
        if all(stats):record='-'.join(x.group(1) for x in stats)+' (promoter profile; verify current record)'
        contact='boxing@matchroom.com' if 'boxing@matchroom.com' in text else ''
        promoter='Matchroom Boxing'
    else:return None
    state=next((s for s,n in STATES.items() if re.search(r'\b'+re.escape(n)+r'\b',hometown,re.I) or re.search(r'(?:,\s*|\s)'+s+r'(?:\b|$)',hometown)),None)
    if not state:return None
    evidence=profile[:850]
    if record and host=='www.goldenboy.com':evidence+=' | Published record counter targets: '+record
    if contact:evidence+=' | Published promoter office: '+contact+' (not a direct boxer contact).'
    return dict(kind='fighter',name=name,city=hometown.split(',')[0].strip()[:120],state=state,
        weight=weight,record=record,source_url=url,evidence=evidence,
        gym_or_manager=promoter+' — official promoter profile',last_activity=activity,
        business_phone=contact if contact.startswith('(') else '',business_email=contact if '@' in contact else '')


def parse_red_owl(raw):
    """The promoter publishes record, hometown and division together in each card."""
    text=plain(raw);rows=[]
    name_nodes=[plain(node) for node in re.findall(r'>([^<>]+)<',raw) if len(node)<180]
    pattern=r"([A-Z][A-Z .’'\-]{2,65}?) (\d+-\d+-\d+|PRO DEBUT)(?: \([^)]*\))? ([A-Z][A-Z .’'\-]{1,60}?), ([A-Z]{2}) ((?:(?:SUPER|LIGHT) )?[A-Z]*WEIGHT)"
    for name,record,city,state,weight in re.findall(pattern,text):
        if state not in STATES:continue
        # The first card follows uppercase marketing copy. Recover the actual
        # name node rather than treating the slogan as part of the boxer name.
        names=[node for node in name_nodes if node and name.endswith(node) and re.fullmatch(r"[A-Z][A-Z .’'\-]+",node)]
        if names:name=max(names,key=len)
        # Preserve the publisher's typo as quoted evidence, normalize the label.
        evidence=f'{name} {record} {city}, {state} {weight}'
        if record=='PRO DEBUT':record='0-0-0 (pro debut listed; verify current record)'
        rows.append(dict(kind='fighter',name=name.strip().title(),record=record+' (promoter roster)',city=city.title(),state=state,
            weight=weight.replace('WELERWEIGHT','WELTERWEIGHT').title(),source_url='https://redowlboxing.com/pages/fighters',
            evidence=evidence,gym_or_manager='Red Owl Boxing — official signed-fighter roster',last_activity='',business_phone='',business_email=''))
    return rows


def fetch_profile(url):
    # Follow only roster links on these exact public publishers, with no arbitrary
    # URL fetch endpoint or redirect to another host.
    if not public_url(url) or urlsplit(url).hostname not in ('toprank.com','www.toprank.com','www.goldenboy.com','www.matchroomboxing.com'):return None
    try:
        response=get_public_page(url,timeout=5)
        if response is not None and response.status_code==200:return parse_profile(url,response.text)
    except requests.RequestException:pass
    return None


def public_profiles():
    global _cache,_cache_at
    with _lock:
        if _cache is not None and time.monotonic()-_cache_at<3600:return _cache
        urls=[];available=0
        for source,pattern in SOURCES:
            try:
                response=get_public_page(source)
                if response is None or response.status_code!=200:continue
                available+=1
                urls.extend(re.findall(pattern,response.text))
            except requests.RequestException:continue
        if not available:raise HTTPException(503,'Public promoter directories are unavailable. Saved prospects remain available; try again later.')
        urls=list(dict.fromkeys(u.replace('https://www.toprank.com/','https://toprank.com/') for u in urls))[:220]
        with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(fetch_profile,urls))
        try:
            response=get_public_page('https://redowlboxing.com/pages/fighters')
            if response is not None and response.status_code==200:rows.extend(parse_red_owl(response.text))
        except requests.RequestException:pass
        _cache=[r for r in rows if r];_cache_at=time.monotonic()
        return _cache


def search_official_rosters(states):
    return {'leads':[dict(row) for row in public_profiles() if row['state'] in states]}
