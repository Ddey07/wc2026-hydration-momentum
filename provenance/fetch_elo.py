import json, urllib.request, time
# SofaScore name -> eloratings file base (spaces->underscores)
NAMEMAP={
 'Côte d\'Ivoire':'Ivory_Coast','USA':'United_States','Türkiye':'Turkey','Czechia':'Czechia',
 'Cabo Verde':'Cape_Verde','DR Congo':'DR_Congo','South Korea':'South_Korea','South Africa':'South_Africa',
 'New Zealand':'New_Zealand','Saudi Arabia':'Saudi_Arabia','Bosnia & Herzegovina':'Bosnia_and_Herzegovina',
 'Curaçao':'Curacao',
}
def base(n): return NAMEMAP.get(n, n.replace(' ','_'))
ko=json.load(open('wc2026_knockout_raw.json')); gp=json.load(open('wc2026_group_momentum.json'))
teams=sorted(set(m['home'] for m in ko+gp)|set(m['away'] for m in ko+gp))
ua={'User-Agent':'Mozilla/5.0'}
series={}   # team -> list of (yyyymmdd, elo)
fails=[]
for t in teams:
    url=f"https://www.eloratings.net/{base(t)}.tsv"
    try:
        req=urllib.request.Request(url,headers=ua)
        txt=urllib.request.urlopen(req,timeout=25).read().decode('utf-8',errors='replace')
    except Exception as e:
        fails.append((t,str(e)[:40])); continue
    rows=[r.split('\t') for r in txt.strip().split('\n') if r]
    # detect team code = code present in col4/col5 of (almost) all rows
    from collections import Counter
    cnt=Counter()
    for r in rows:
        if len(r)>=5: cnt[r[3]]+=1; cnt[r[4]]+=1
    code=cnt.most_common(1)[0][0]
    ser=[]
    for r in rows:
        if len(r)<12: continue
        try:
            d=int(r[0])*10000+int(r[1])*100+int(r[2])
            if r[3]==code: elo=float(r[10])
            elif r[4]==code: elo=float(r[11])
            else: continue
            ser.append((d,elo))
        except: continue
    ser.sort()
    series[t]={'code':code,'series':ser}
    time.sleep(0.15)
json.dump(series, open('elo/intl_elo_series.json','w'))
print("teams fetched:",len(series),"/",len(teams))
if fails: print("FAILS:",fails)
# sanity: Spain latest
sp=series.get('Spain',{}).get('series',[])[-3:]
print("Spain last:",sp)
print("Argentina last:",series.get('Argentina',{}).get('series',[])[-2:])
