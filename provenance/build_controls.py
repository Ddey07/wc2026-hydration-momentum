# Generalized control-candidate builder. Usage: python build_controls.py file1:tier1 file2:tier2 ...
import json, math, datetime as dt, sys, os
from concurrent.futures import ThreadPoolExecutor
import urllib.request
elo=json.load(open('elo/intl_elo_series.json'))
WXCACHE='wx_archive_cache.json'
wxc=json.load(open(WXCACHE)) if os.path.exists(WXCACHE) else {}

def wbgt(Ta,rh):
    e=(rh/100.0)*6.105*math.exp(17.27*Ta/(237.7+Ta)); return 0.567*Ta+0.393*e+3.94
def elo_before(team,ymd):
    s=elo.get(team,{}).get('series',[]); v=None
    for d,e in s:
        if d<ymd: v=e
        else: break
    return v
def wx_fetch(k):
    lat,lon,ymd=k
    key=f"{round(lat,2)},{round(lon,2)},{ymd}"
    if key in wxc: return key,wxc[key]
    dd=dt.datetime.strptime(str(ymd),'%Y%m%d'); d0=(dd-dt.timedelta(days=1)).strftime('%Y-%m-%d'); d1=(dd+dt.timedelta(days=1)).strftime('%Y-%m-%d')
    url=(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={d0}&end_date={d1}"
         f"&hourly=temperature_2m,relative_humidity_2m&timezone=auto")
    for a in range(4):
        try:
            j=json.load(urllib.request.urlopen(url,timeout=40)); return key,{'h':j['hourly'],'off':j['utc_offset_seconds']}
        except Exception:
            if a==3: return key,None
ACCITY={'Houston','Arlington','Dallas','Atlanta','Las Vegas','Glendale'}  # fully air-conditioned / domed venues
def mom_at(mom,s,mn):
    i=mn-s; return mom[i] if 0<=i<len(mom) else None
def wmean(mom,s,lo,hi):
    vs=[mom_at(mom,s,x) for x in range(lo,hi+1)]; vs=[x for x in vs if x is not None]
    return sum(vs)/len(vs) if vs else None
def wslope(mom,s,lo,hi):
    pts=[(x,mom_at(mom,s,x)) for x in range(lo,hi+1)]; pts=[(x,v) for x,v in pts if v is not None]
    n=len(pts)
    if n<2: return None
    mx=sum(x for x,_ in pts)/n; my=sum(v for _,v in pts)/n
    den=sum((x-mx)**2 for x,_ in pts); return (sum((x-mx)*(v-my) for x,v in pts)/den) if den else None
def score_before(goals,mn):
    hs=as_=0
    for g in goals:
        if g['mn']+(g.get('at') or 0)/100.0<mn:
            if g['h']: hs+=1
            else: as_+=1
    return hs,as_

specs=[a.split(':') for a in sys.argv[1:]]
matches=[]
for fn,tier in specs:
    for m in json.load(open(fn)):
        if isinstance(m.get('mom'),list) and len(m['mom'])>10 and m.get('lat') is not None:
            m['_tier']=tier; matches.append(m)
# weather
keys={}
for m in matches:
    ymd=int(dt.datetime.utcfromtimestamp(m['ts']).strftime('%Y%m%d'))
    keys[(round(m['lat'],2),round(m['lon'],2),ymd)]=(m['lat'],m['lon'],ymd)
todo=[k for k in keys.values() if f"{round(k[0],2)},{round(k[1],2)},{k[2]}" not in wxc]
print(f"{len(matches)} control matches, {len(todo)} new weather calls")
with ThreadPoolExecutor(max_workers=12) as ex:
    for key,v in ex.map(wx_fetch, todo): wxc[key]=v
json.dump(wxc,open(WXCACHE,'w'))
MINS=list(range(21,31))+list(range(66,77))
rows=[]; missElo=set()
for m in matches:
    ymd=int(dt.datetime.utcfromtimestamp(m['ts']).strftime('%Y%m%d'))
    eh=elo_before(m['home'],ymd); ea=elo_before(m['away'],ymd)
    if eh is None: missElo.add(m['home'])
    if ea is None: missElo.add(m['away'])
    ac=m.get('city') in ACCITY
    w=wxc.get(f"{round(m['lat'],2)},{round(m['lon'],2)},{ymd}")
    Ta=rh=lhour=WB=None
    if w:
        loc=dt.datetime.utcfromtimestamp(m['ts'])+dt.timedelta(seconds=w['off']); lhour=loc.hour
        key=loc.strftime('%Y-%m-%dT%H:00')
        try:
            i=w['h']['time'].index(key); Ta=w['h']['temperature_2m'][i]; rh=w['h']['relative_humidity_2m'][i]
            if Ta is not None and rh is not None: WB=round(wbgt(Ta,rh),1)
        except: pass
    if ac: WB=20.7; Ta=21.0
    brks=set(m.get('breaks') or [])
    s=m['startMin']; mom=m['mom']
    for c in MINS:
        if any(abs(c-b)<=3 for b in brks): continue  # exclude near own break
        pre=wmean(mom,s,c-5,c-1); post=wmean(mom,s,c+1,c+5); sl=wslope(mom,s,c-5,c-1)
        if pre is None or post is None or sl is None or WB is None or eh is None or ea is None: continue
        hs,as_=score_before(m['goals'],c)
        if hs>as_: o=1;margin=hs-as_;lsd='home'
        elif as_>hs: o=-1;margin=as_-hs;lsd='away'
        else: o=1 if pre>=0 else -1;margin=0;lsd='level'
        rows.append({'unit':f"C{m['id']}_{c}",'treated':0,'tier':m['_tier'],'comp':m.get('comp',m['_tier']),'match_id':m['id'],
            'half':'H1' if c<45 else 'H2','minute':c,'margin':margin,'leadside':lsd,'orient':o,
            'pre_level':round(o*pre,2),'pre_slope':round(o*sl,3),'post_level':round(o*post,2),
            'wbgt':WB,'local_hour':lhour,'elo_gap_or':round((eh-ea)*o,1)})
json.dump(rows,open('control_candidates_all.json','w'))
from collections import Counter
print("candidate rows:",len(rows),"| by tier:",dict(Counter(r['tier'] for r in rows)),
      "| matches:",len(set(r['match_id'] for r in rows)))
if missElo: print("missing Elo teams:",sorted(missElo)[:20])
