"""Sourced local business discovery without a paid AI dependency or outreach."""
import copy
import ipaddress
import json
import math
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
import requests

GYM_ADDRESS = '8416 NW Expressway, Oklahoma City, OK 73162'
GYM_LAT, GYM_LON = 35.56871056141, -97.66325776497
SNAPSHOT = Path(__file__).with_name('data') / 'nw_okc_businesses.json'
HEADERS = {'User-Agent':'TNGOS-SponsorLocator/1.0 (marketing@tngboxinggym.com)'}
AMENITIES = {'restaurant','cafe','fast_food','bank','dentist','clinic','pharmacy','veterinary','fuel','car_wash','car_rental'}
OFFICES = {'insurance','estate_agent','financial','accountant','lawyer','company'}
CACHE = {}
LOCK = threading.Lock()


def distance_miles(lat1, lon1, lat2, lon2):
    a,b=math.radians(lat1),math.radians(lat2)
    h=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(math.radians(lon2-lon1)/2)**2
    return 3958.7613*2*math.asin(min(1,math.sqrt(h)))


def public_url(value):
    try:
        p=urlsplit(str(value or '').strip())
        if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:
            return None
        if p.hostname.lower() in ('localhost','localhost.localdomain') or '.' not in p.hostname:
            return None
        try:
            if not ipaddress.ip_address(p.hostname).is_global:return None
        except ValueError:pass
        return urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
    except ValueError:return None


def geocode(address):
    # Stable Census-derived approximate business-search center, not a geofence pin.
    key=re.sub(r'[^a-z0-9]','',address.lower()).replace('northwest','nw').replace('expressway','expy')
    if '8416nwexpy' in key and ('73162' in key or 'oklahomacity' in key):
        return {'lat':GYM_LAT,'lon':GYM_LON,'address':GYM_ADDRESS,'source':'U.S. Census geocoder (approximate)'}
    try:
        r=requests.get('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress',
            params={'address':address,'benchmark':'Public_AR_Current','format':'json'},headers=HEADERS,timeout=6)
        r.raise_for_status()
        matches=r.json().get('result',{}).get('addressMatches',[])
        if len(matches)!=1:raise ValueError('Ambiguous address')
        c=matches[0]['coordinates'];lat,lon=float(c['y']),float(c['x'])
        if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):raise ValueError()
        return {'lat':lat,'lon':lon,'address':matches[0]['matchedAddress'],'source':'U.S. Census geocoder (approximate)'}
    except (requests.RequestException,ValueError,KeyError,TypeError):
        raise RuntimeError('The search address could not be located. Enter a full U.S. street address, city, state, and ZIP code.')


def map_records(center, radius):
    # Small, cached map extract; intentionally a sample rather than exhaustive POI crawling.
    span=min(float(radius),2.0);dy=span/69;dx=span/(69*max(.2,math.cos(math.radians(center['lat']))))
    bbox=f"{center['lon']-dx},{center['lat']-dy},{center['lon']+dx},{center['lat']+dy}"
    r=requests.get('https://api.openstreetmap.org/api/0.6/map',params={'bbox':bbox},headers=HEADERS,timeout=12)
    r.raise_for_status()
    if len(r.content)>12_000_000:raise ValueError('Map extract too large')
    root=ET.fromstring(r.content)
    nodes={n.attrib['id']:(float(n.attrib['lat']),float(n.attrib['lon'])) for n in root.findall('node')}
    elements=[]
    for e in root:
        tags={t.attrib['k']:t.attrib['v'] for t in e.findall('tag')}
        if not tags.get('name') or not any(k in tags for k in ('shop','amenity','office')):continue
        if e.tag=='node':lat,lon=nodes[e.attrib['id']]
        elif e.tag=='way':
            coords=[nodes[n.attrib['ref']] for n in e.findall('nd') if n.attrib['ref'] in nodes]
            if not coords:continue
            lat=sum(c[0] for c in coords)/len(coords);lon=sum(c[1] for c in coords)/len(coords)
        else:continue
        elements.append({'type':e.tag,'id':int(e.attrib['id']),'lat':lat,'lon':lon,'tags':tags})
    return {'elements':elements,'retrieved_at':datetime.now(timezone.utc).isoformat(),
        'source_url':'https://api.openstreetmap.org/api/0.6/map?'+urlencode({'bbox':bbox}),
        'coverage_note':'Nearby map sample, not a complete business directory. Verify current details and sponsorship interest.'}


def business_leads(data, center, radius, category, event_name, max_results):
    results={}
    for e in data.get('elements',[]):
        try:
            tags=e['tags'];name=str(tags.get('name') or '').strip()[:180]
            if not name or tags.get('disused')=='yes' or tags.get('abandoned')=='yes':continue
            shop=tags.get('shop','');amenity=tags.get('amenity','');office=tags.get('office','')
            if not shop and amenity not in AMENITIES and office not in OFFICES:continue
            if shop in ('vacant','no'):continue
            industry=(shop or amenity or office).replace('_',' ')
            group='automotive' if shop in ('car','car_repair','tyres','car_parts') or amenity in ('car_wash','car_rental','fuel') else 'food' if amenity in ('restaurant','cafe','fast_food') or shop in ('bakery','butcher','supermarket','convenience') else 'health' if amenity in ('dentist','clinic','pharmacy','veterinary') or shop in ('optician','hearing_aids') else 'finance' if amenity=='bank' or office in ('insurance','financial','accountant') else 'retail'
            if category and category!='all' and category!=group:continue
            lat,lon=float(e['lat']),float(e['lon'])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):continue
            miles=distance_miles(center['lat'],center['lon'],lat,lon)
            if miles>radius:continue
            if e['type'] not in ('node','way','relation') or int(e['id'])<=0:continue
            source=f"https://www.openstreetmap.org/{e['type']}/{int(e['id'])}"
            website=public_url(tags.get('website') or tags.get('contact:website'))
            email=str(tags.get('email') or tags.get('contact:email') or '').strip()
            if not re.fullmatch(r'[^\s@;,]+@[^\s@;,]+\.[^\s@;,]+',email):email=None
            address=' '.join(str(tags.get(k) or '').strip() for k in ('addr:housenumber','addr:street')).strip()
            row={'business_name':name,'website':website,'phone':str(tags.get('phone') or tags.get('contact:phone') or '')[:80] or None,
                'email':email,'address':address or None,'city':tags.get('addr:city') or None,'state':tags.get('addr:state') or None,
                'zip_code':tags.get('addr:postcode') or None,'latitude':lat,'longitude':lon,'industry':industry,
                'why_good_fit':f'Nearby {industry} to review for {event_name}. Sponsorship interest, budget, and history are unverified.',
                'distance_miles':round(miles,2),'marketing_evidence':[],'sponsorship_evidence':[],
                'source_urls':[source]+([website] if website else []),'marketing_activity_score':0,'sponsorship_history_score':0,
                'audience_fit_score':0,'business_capacity_score':0,'distance_score':max(0,round(100*(1-miles/radius))),
                'relationship_score':0,'discovery_score':0,'marketing_propensity':'UNKNOWN',
                'verified_sponsorship_history':None,'lead_source':'OPENSTREETMAP','source_checked_at':data.get('retrieved_at')}
            # One closest location per business name; do not conflate map duplicates with extra leads.
            if name.casefold() not in results or miles<results[name.casefold()]['distance_miles']:results[name.casefold()]=row
        except (KeyError,TypeError,ValueError,OverflowError):continue
    return sorted(results.values(),key=lambda x:x['distance_miles'])[:max_results]


def search_sponsors(*,event_name,event_address,radius_miles=5,category=None,max_results=20,refresh=False):
    center=geocode(event_address)
    key=(round(center['lat'],4),round(center['lon'],4),round(min(radius_miles,2),2))
    data=None;source='LIVE_MAP'
    with LOCK:
        cached=CACHE.get(key)
        if cached and time.monotonic()-cached[0]<86400 and not refresh:
            data=copy.deepcopy(cached[1]);source='CACHED_MAP'
    near_gym=distance_miles(center['lat'],center['lon'],GYM_LAT,GYM_LON)<.25
    if data is None and near_gym and not refresh:
        data=json.loads(SNAPSHOT.read_text());source='SAVED_MAP_SNAPSHOT'
    if data is None:
        try:
            data=map_records(center,radius_miles)
            with LOCK:
                if len(CACHE)>=64:CACHE.pop(next(iter(CACHE)))
                CACHE[key]=(time.monotonic(),copy.deepcopy(data))
        except (requests.RequestException,ValueError,ET.ParseError,KeyError,TypeError):
            if near_gym:
                data=json.loads(SNAPSHOT.read_text());source='SAVED_MAP_SNAPSHOT'
            else:raise RuntimeError('The public business directory is unavailable. Try again shortly or open the local map search. No outreach was sent.')
    rows=business_leads(data,center,radius_miles,category,event_name,max_results)
    return {'results':rows,'count':len(rows),'search_address':center['address'],'search_center':center,
        'search_source':source,'source_checked_at':data.get('retrieved_at'),
        'notice':('Using a saved public-map snapshot. ' if source=='SAVED_MAP_SNAPSHOT' else 'Using public map records. ')+data.get('coverage_note','Nearby sample; verify details.'),
        'attribution':'© OpenStreetMap contributors','attribution_url':'https://www.openstreetmap.org/copyright',
        'map_search_url':'https://www.google.com/maps/search/?'+urlencode({'api':1,'query':f'businesses near {center["address"]}'})}


def run_sponsor_scout(**kwargs):
    return search_sponsors(**kwargs)['results']
