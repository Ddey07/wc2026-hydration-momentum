import json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
rng=np.random.default_rng(11)
raw={}; goals={}
def add(fn):
    try: data=json.load(open(fn))
    except: return
    for m in data:
        if isinstance(m.get('mom'),list) and len(m['mom'])>10:
            raw[m['id']]=(m['startMin'],m['mom']); goals[m['id']]=m.get('goals',[])
for f in ['data/wc2026_knockout_raw.json','data/wc2026_group_momentum.json','data/wc_control_intl.json',
          'data/wc_control_pastwc.json','data/wc_control_group_momentum.json','data/wc_control_momentum.json']: add(f)
gv={x['id']:x for x in json.load(open('data/_gv.json'))}
_city={}
for _m in json.load(open('data/wc2026_knockout_raw.json')): _city[_m['id']]=_m.get('city')
for _mid,_g in gv.items(): _city.setdefault(_mid,_g.get('city'))
ACCITY={'Houston','Arlington','Dallas','Atlanta','Las Vegas','Glendale'}
def valid_len(mid):
    if mid not in raw: return False
    L=len(raw[mid][1]); return (80<=L<=100) or (118<=L<=128)
END={}
for m in json.load(open('data/wc2026_group_momentum.json')):
    for b in m.get('breaks',[]):
        if 'start' in b and 'end' in b:
            w=b['end']-b['start']; END[(m['id'],b['start'])]=b['end'] if 2<=w<=4 else b['start']+3
def resume(mid,s): return END.get((mid,s), s+3)
def wmean(mid,c,lo,hi):
    s,mom=raw[mid]; vs=[mom[c+k-s] for k in range(lo,hi+1) if 0<=c+k-s<len(mom)]; return np.mean(vs) if vs else None
def wslope(mid,c,lo,hi):
    s,mom=raw[mid]; p=[(k,mom[c+k-s]) for k in range(lo,hi+1) if 0<=c+k-s<len(mom)]
    if len(p)<2: return None
    x=np.array([a for a,_ in p]); y=np.array([b for _,b in p]); return np.polyfit(x,y,1)[0]
def opost(mid,c,o,lo,hi):
    s,mom=raw[mid]; vs=[mom[c+k-s] for k in range(lo,hi+1) if 0<=c+k-s<len(mom)]; return o*np.mean(vs) if vs else np.nan
def sb(mid,mn):
    hs=a=0
    for g in goals.get(mid,[]):
        if g['mn']+(g.get('at') or 0)/100.0<mn: hs+=g['h']; a+=(not g['h'])
    return hs,a
def ebal(Xc,tgt):
    Z=Xc-tgt
    def loss(l): a=-Z@l; a-=a.max(); return np.log(np.exp(a).sum())
    def grad(l): a=-Z@l; a-=a.max(); e=np.exp(a); w=e/e.sum(); return -(w@Z)
    r=minimize(loss,np.zeros(Z.shape[1]),jac=grad,method='L-BFGS-B',options={'maxiter':800})
    a=-Z@r.x; a-=a.max(); e=np.exp(a); return e/e.sum()

DROP='15186769'
trc=pd.DataFrame(json.load(open('data/treated_covariates.json')))
coc=pd.DataFrame(json.load(open('data/control_candidates_all.json')))
ELO_T={r['match_id']:(r['elo_home'],r['elo_away']) for _,r in trc.iterrows()}
def build_row(mid,c,treated,extra):
    if mid not in raw: return None
    pm=wmean(mid,c,-5,-1); sl=wslope(mid,c,-5,-1)
    if pm is None or sl is None: return None
    o=1 if pm>=0 else -1
    hs,a=sb(mid,c); smarg=o*(hs-a)
    yA=opost(mid,c,o,3,12)
    if treated:
        e=resume(mid,c); yB=opost(mid,c,o,e-c,e-c+9)
        eh,ea=ELO_T.get(mid,(np.nan,np.nan)); elo=o*(eh-ea)
        wb=20.7 if _city.get(mid) in ACCITY else extra['wbgt']
    else:
        yB=opost(mid,c,o,1,10)
        elo=o*extra['elo_gap_or']*extra['orient']       # de-orient then re-orient by dominance
        wb=extra['wbgt']
    if not np.isfinite(yA) or not np.isfinite(yB) or not np.isfinite(elo) or wb is None: return None
    return dict(match_id=mid,minute=c,treated=treated,half='H1' if c<45 else 'H2',
                wbgt=wb,local_hour=extra['local_hour'],elo=elo,smargin=smarg,
                pre_level=o*pm,pre_slope=o*sl,yA=yA,yB=yB)
rows=[]
for _,r in trc.iterrows():
    if not valid_len(r['match_id']) or r['match_id']==DROP: continue
    rr=build_row(r['match_id'],int(r['minute']),1,{'wbgt':r['wbgt'],'local_hour':r['local_hour']})
    if rr: rows.append(rr)
for _,r in coc.iterrows():
    rr=build_row(r['match_id'],int(r['minute']),0,{'wbgt':r['wbgt'],'local_hour':r['local_hour'],'elo_gap_or':r['elo_gap_or'],'orient':r['orient']})
    if rr: rows.append(rr)
F=pd.DataFrame(rows)
COV=['wbgt','local_hour','elo','smargin','minute','pre_level','pre_slope']
print('DOMINANCE-ORIENTED external analysis | treated=%d control=%d'%(int(F.treated.sum()),int((1-F.treated).sum())))
print('treated signed-margin dist:', dict(pd.Series(F[F.treated==1].smargin.astype(int)).value_counts().sort_index()))
mu=F[COV].mean().values; sd=F[COV].std().values
def att(col, sub=None):
    G=F if sub is None else F[sub]
    num=den=0
    for hf in ['H1','H2']:
        T=G[(G.half==hf)&(G.treated==1)]; C=G[(G.half==hf)&(G.treated==0)]
        if len(T)<3 or len(C)<10: continue
        Xt=(T[COV].values-mu)/sd; Xc=(C[COV].values-mu)/sd; w=ebal(Xc,Xt.mean(0))
        yt=np.nanmean(T[col].values); ya=C[col].values; fin=np.isfinite(ya)
        yc=np.sum(w[fin]*ya[fin])/np.sum(w[fin]); num+=len(T)*(yt-yc); den+=len(T)
    return num/den if den else np.nan
print('\n=== ENTROPY-BALANCED ATT (all on-support) ===')
print('  Design A (clock)  %+.2f'%att('yA'))
print('  Design B (play)   %+.2f'%att('yB'))
# tight caliper matching
Z=(F[COV].values-mu)/sd; tm=F.treated.values==1
ps=LogisticRegression(max_iter=1000).fit(Z,F.treated.values).predict_proba(Z)[:,1]
lg=np.log(np.clip(ps,1e-6,1-1e-6)/np.clip(1-ps,1e-6,1-1e-6)); cal=0.2*lg.std()
Ti=np.where(tm)[0]; Ci=np.where(~tm)[0]
d_,ix=NearestNeighbors(n_neighbors=1).fit(lg[Ci].reshape(-1,1)).kneighbors(lg[Ti].reshape(-1,1))
ok=d_[:,0]<=cal
print('\n=== TIGHT-CALIPER MATCHING (0.2 SD) | matched=%d dropped=%d ==='%(ok.sum(),(~ok).sum()))
drp=F.iloc[Ti[~ok]]
if len(drp): print('  dropped: WBGT %.1f, %%kickoff<=14h %.0f'%(drp.wbgt.mean(),100*(drp.local_hour<=14).mean()))
for lab,col in [('Design A','yA'),('Design B','yB')]:
    yt=F[col].values[Ti[ok]]; yc=F[col].values[Ci[ix[ok,0]]]; dd=(yt-yc); dd=dd[np.isfinite(dd)]
    se=dd.std()/np.sqrt(len(dd)); print('  %-9s matched ATT %+.2f [%+.2f,%+.2f]'%(lab,dd.mean(),dd.mean()-1.96*se,dd.mean()+1.96*se))
# CATE by lead-state (Design B)
def leadstate(m): return 'a_behind' if m<0 else ('b_level' if m==0 else ('c_ahead1' if m==1 else 'd_ahead2+'))
F['lead']=[leadstate(m) for m in F.smargin]
def cate_ci(sub, cov, col='yB'):
    G=F[sub]; T=G[G.treated==1]; C=G[G.treated==0]
    if len(T)<5 or len(C)<20: return None,len(T),(np.nan,np.nan)
    m0=F[cov].mean().values; s0=F[cov].std().values
    def one(T,C):
        Xt=(T[cov].values-m0)/s0; Xc=(C[cov].values-m0)/s0; w=ebal(Xc,Xt.mean(0))
        ya=C[col].values; fin=np.isfinite(ya); return np.nanmean(T[col].values)-np.sum(w[fin]*ya[fin])/np.sum(w[fin])
    est=one(T,C); ut=T.match_id.unique(); uc=C.match_id.unique(); bs=[]
    for _ in range(200):
        tb=T[T.match_id.isin(rng.choice(ut,len(ut),True))]; cb=C[C.match_id.isin(rng.choice(uc,len(uc),True))]
        if len(tb)<5 or len(cb)<20: continue
        try: bs.append(one(tb,cb))
        except: pass
    lo,hi=np.percentile(bs,[2.5,97.5]) if bs else (np.nan,np.nan); return est,len(T),(lo,hi)
COV2=[c for c in COV if c!='smargin']
print('\n=== CATE by dominance-signed lead (Design B, external) ===')
for L in ['a_behind','b_level','c_ahead1','d_ahead2+']:
    a,n,ci=cate_ci(F.lead==L,COV2)
    print('  %-10s n=%3d  ATT_B %s'%(L,n,'%+.2f [%+.2f,%+.2f]'%(a,ci[0],ci[1]) if a is not None else '(thin)'))
print('\n=== CATE by heat (Design B, external) ===')
for L,mask in [('cool WBGT<28',F.wbgt<28),('hot WBGT>=28',F.wbgt>=28)]:
    a,n,ci=cate_ci(mask,COV)
    print('  %-14s n=%3d  ATT_B %s'%(L,n,'%+.2f [%+.2f,%+.2f]'%(a,ci[0],ci[1]) if a is not None else '(thin)'))
