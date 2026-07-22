import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
raw={};goals={};breaks={};citym={}
kob={m['id']:m['breakMins'] for m in json.load(open('data/break_times_exact.json'))}
gv={x['id']:x for x in json.load(open('data/_gv.json'))}
for m in json.load(open('data/wc2026_knockout_raw.json')):
    if isinstance(m.get('mom'),list) and len(m['mom'])>10:
        raw[m['id']]=(m['startMin'],m['mom']);goals[m['id']]=m['goals'];breaks[m['id']]=sorted(kob.get(m['id'],[]));citym[m['id']]=m.get('city')
for m in json.load(open('data/wc2026_group_momentum.json')):
    if isinstance(m.get('mom'),list) and len(m['mom'])>10:
        raw[m['id']]=(m['startMin'],m['mom']);goals[m['id']]=m['goals'];breaks[m['id']]=sorted(set(b['start'] for b in m.get('breaks',[])));citym[m['id']]=gv.get(m['id'],{}).get('city')
rawwb={r['match_id']:r['wbgt'] for r in json.load(open('data/treated_covariates.json'))}
ACCITY={'Houston','Arlington','Dallas','Atlanta','Las Vegas','Glendale'}
def WB(mid): return 20.7 if citym.get(mid) in ACCITY else rawwb.get(mid)
def period(m): return 1 if m<=45 else (2 if m<=90 else (3 if m<=105 else 4))
def mom_at(mid,mn): s,mo=raw[mid];i=mn-s;return mo[i] if 0<=i<len(mo) else None
def wm(mid,lo,hi):
    vs=[mom_at(mid,x) for x in range(lo,hi+1)];vs=[v for v in vs if v is not None];return sum(vs)/len(vs) if vs else None
def wsl(mid,lo,hi):
    p=[(x,mom_at(mid,x)) for x in range(lo,hi+1)];p=[(x,v) for x,v in p if v is not None];n=len(p)
    if n<2:return None
    mx=sum(x for x,_ in p)/n;my=sum(v for _,v in p)/n;den=sum((x-mx)**2 for x,_ in p)
    return sum((x-mx)*(v-my) for x,v in p)/den if den else None
def sb(mid,mn):
    hs=a=0
    for g in goals[mid]:
        if g['mn']+(g.get('at') or 0)/100.0<mn: hs+=g['h'];a+=(not g['h'])
    return hs,a
def row(mid,c,brk,hi):
    pre=wm(mid,c-5,c-1);sl=wsl(mid,c-5,c-1)
    if pre is None or sl is None: return None
    s,mo=raw[mid];last=s+len(mo)-1
    if c-5<s or c+hi>last or period(c-5)!=period(c+hi): return None
    for b in breaks.get(mid,[]):
        if (not brk) and c-5<=b<=c+hi: return None
    if not brk and 43<=c<=48: return None
    hs,a=sb(mid,c)
    if hs>a:o=1;mg=hs-a
    elif a>hs:o=-1;mg=a-hs
    else:o=1 if pre>=0 else -1;mg=0
    post=[mom_at(mid,c+k) for k in range(1,hi+1)];post=[v for v in post if v is not None]
    if not post: return None
    return dict(match_id=str(mid),brk=brk,minute=c,half=int(c>=45),wbgt=WB(mid),
        pre_level=o*pre,pre_slope=o*sl,margin=mg,Y=o*np.mean(post))
def build(hi):
    R=[]
    for mid,bks in breaks.items():
        for c in bks:
            r=row(mid,c,1,hi)
            if r and r['wbgt'] is not None: R.append(r)
    for mid,(s,mo) in raw.items():
        for c in range(s+5,s+len(mo)-5):
            if any(abs(c-b)<=3 for b in breaks.get(mid,[])): continue
            r=row(mid,c,0,hi)
            if r and r['wbgt'] is not None: R.append(r)
    d=pd.DataFrame(R); d['wbgt_c']=d['wbgt']-d['wbgt'].mean(); d['m2']=d['minute']**2
    return d
def fit(hi):
    d=build(hi)
    nb=int(d.brk.sum()); nc=int((1-d.brk).sum()); nm=d.match_id.nunique()
    # within-match FE (ANCOVA): Y ~ break + break:wbgt_c + phase + situation + match FE
    f="Y ~ brk + brk:wbgt_c + minute + m2 + C(half) + pre_level + pre_slope + margin + C(match_id)"
    r=smf.ols(f,data=d).fit(cov_type='cluster',cov_kwds={'groups':d['match_id']})
    b=r.params;cov=r.cov_params()
    def lc(w):  # break effect at wbgt=w : coef(brk) + coef(brk:wbgt_c)*(w-mean)
        wc=w-d['wbgt'].mean(); v=b['brk']+b['brk:wbgt_c']*wc
        se=np.sqrt(cov.loc['brk','brk']+wc**2*cov.loc['brk:wbgt_c','brk:wbgt_c']+2*wc*cov.loc['brk','brk:wbgt_c'])
        return v,v-1.96*se,v+1.96*se
    print(f"\n=== Within-match FE regression, outcome = oriented mean momentum over post 1-{hi} ===")
    print(f"    break minutes n={nb} | control minutes n={nc} | matches={nm}  (uses ALL controls, not K=8)")
    print(f"    break main effect (at mean WBGT {d['wbgt'].mean():.1f}): {b['brk']:+.2f}  CI[{b['brk']-1.96*r.bse['brk']:+.2f},{b['brk']+1.96*r.bse['brk']:+.2f}]")
    print(f"    break x WBGT interaction: {b['brk:wbgt_c']:+.3f} per C  CI[{b['brk:wbgt_c']-1.96*r.bse['brk:wbgt_c']:+.3f},{b['brk:wbgt_c']+1.96*r.bse['brk:wbgt_c']:+.3f}]  (p={r.pvalues['brk:wbgt_c']:.3f})")
    for w in [22,28,32]:
        v,lo,hi2=lc(w); print(f"    implied break effect @WBGT {w}: {v:+.2f}  CI[{lo:+.2f},{hi2:+.2f}]")
    # pre-trend falsification: same model with pre-break window as pseudo-outcome
    return
for hi in [10,15]: fit(hi)
