import json, urllib.request, time, math, datetime as dt
d=json.load(open('wc2026_knockout_raw.json'))
LATLON={
 'Inglewood':(33.9535,-118.3392),'Houston':(29.6847,-95.4107),'Foxborough':(42.0909,-71.2643),
 'Monterrey':(25.6690,-100.2443),'Arlington':(32.7473,-97.0945),'East Rutherford':(40.8135,-74.0745),
 'Mexico City':(19.3029,-99.1505),'Atlanta':(33.7554,-84.4009),'Seattle':(47.5952,-122.3316),
 'Santa Clara':(37.4030,-121.9698),'Toronto':(43.6332,-79.4185),'Vancouver':(49.2768,-123.1120),
 'Miami Gardens':(25.9580,-80.2389),'Kansas City':(39.0489,-94.4839),'Philadelphia':(39.9008,-75.1675)}
def wbgt(Ta,rh):
    e=(rh/100.0)*6.105*math.exp(17.27*Ta/(237.7+Ta))
    return 0.567*Ta+0.393*e+3.94
cache={}
out={}
for m in d:
    city=m['city']; lat,lon=LATLON[city]
    khour=dt.datetime.utcfromtimestamp(m['ts']).strftime('%Y-%m-%dT%H:00')
    key=(round(lat,3),round(lon,3))
    if key not in cache:
        url=(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             f"&past_days=92&forecast_days=1&hourly=temperature_2m,relative_humidity_2m&timezone=UTC")
        for attempt in range(3):
            try:
                j=json.load(urllib.request.urlopen(url,timeout=30)); cache[key]=j['hourly']; break
            except Exception as ex:
                if attempt==2: cache[key]={'time':[],'temperature_2m':[],'relative_humidity_2m':[]}; print("WX FAIL",city,ex)
                time.sleep(2)
    h=cache[key]
    try:
        i=h['time'].index(khour)
        Ta=h['temperature_2m'][i]; rh=h['relative_humidity_2m'][i]
        out[m['id']]={'tempC':Ta,'rh':rh,'wbgt':round(wbgt(Ta,rh),1),'khour':khour,'city':city,'roof':m['venue']}
    except Exception as ex:
        out[m['id']]={'tempC':None,'rh':None,'wbgt':None,'khour':khour,'city':city}
        print("hour miss",city,khour,ex)
    time.sleep(0.3)
json.dump(out,open('temps_2026.json','w'),indent=0)
# summary
rows=[(m['home'][:12]+' v '+m['away'][:12], out[m['id']]['city'], out[m['id']]['tempC'], out[m['id']]['wbgt']) for m in d]
print(f"{'MATCH':30} {'CITY':16} {'TempC':>6} {'WBGT':>6}")
for r in rows:
    t = f"{r[2]:.1f}" if r[2] is not None else "NA"
    w = f"{r[3]:.1f}" if r[3] is not None else "NA"
    print(f"{r[0]:30} {r[1]:16} {t:>6} {w:>6}")
vals=[out[m['id']]['tempC'] for m in d if out[m['id']]['tempC'] is not None]
print(f"\nGot temps for {len(vals)}/32. Range {min(vals):.1f}-{max(vals):.1f}C, median {sorted(vals)[len(vals)//2]:.1f}C")
