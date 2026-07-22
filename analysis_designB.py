"""
Design B (frozen-momentum / play-aligned) pipeline, mirroring analysis_gap.py.
Counterfactual: the break is dead time and momentum is frozen during it. The resume minute is play +1.
CASE/CONTROL matching (careful):
  - a CASE (break) at start minute s, with resume e = break end (per-match; group 'end', else s+3),
    has outcome window over PLAY minutes [e, e+H-1] (i.e. from resumption), pre-window [s-5,s-1], anchor = s.
  - a CONTROL (non-break) at minute c has outcome window over its immediate PLAY minutes [c+1, c+H]
    (continuous play, no break removed), pre-window [c-5,c-1], anchor = c.
  Both windows are H minutes of PLAY after the anchor; the covariates and time trend use the anchor minute,
  so the break contrast is play-aligned.  (Design A instead uses [c+GAP,c+GAP+H-1] for BOTH.)
"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
exec(open('analysis_gap.py').read().split('if __name__')[0])   # loaders, valid_len, DROP, GAP, elo_h/elo_a

END={}
for m in json.load(open('data/wc2026_group_momentum.json')):
    for b in m.get('breaks',[]):
        if 'start' in b and 'end' in b:
            w=b['end']-b['start']; END[(m['id'],b['start'])]=b['end'] if 2<=w<=4 else b['start']+3
def resume(mid,s): return END.get((mid,s), s+3)   # per-match resume minute (knockout imputed s+3)

def omean(mid,lo,hi):
    vs=[mom_at(mid,x) for x in range(lo,hi+1)]; vs=[v for v in vs if v is not None]
    return float(np.mean(vs)) if vs else None

def rowB(mid,c,brk,H):
    pre=wm(mid,c-5,c-1); sl=wsl(mid,c-5,c-1)
    if pre is None or sl is None: return None
    o=1 if pre>=0 else -1
    lo,hi=(resume(mid,c), resume(mid,c)+H-1) if brk else (c+1, c+H)   # play-aligned windows
    s,mo=raw[mid]; last=s+len(mo)-1
    if c-5<s or hi>last or period(c-5)!=period(hi): return None
    y=omean(mid,lo,hi)
    if y is None: return None
    hs,a=sb(mid,c); w=WB(mid); m=str(mid)
    if w is None or m not in elo_h: return None
    return dict(match_id=m,brk=brk,minute=c,m2=c*c,half=int(c>=45),wbgt=w,
                pre_level=o*pre,pre_slope=o*sl,margin=o*(hs-a),elo_gap=o*(elo_h[m]-elo_a[m]),Y=o*y)

def build_B(H):
    R=[]
    for mid,bks in breaks.items():
        if not valid_len(mid): continue
        for c in bks:
            r=rowB(mid,c,1,H)
            if r: R.append(r)
    for mid,(s,mo) in raw.items():
        if not valid_len(mid): continue
        for c in range(s+5, s+len(mo)-1):
            if any(b-2<=c<=b+GAP+H for b in breaks.get(mid,[])): continue
            if 43<=c<=48: continue
            r=rowB(mid,c,0,H)
            if r: R.append(r)
    d=pd.DataFrame(R); d=d[d.match_id!=DROP].copy()
    d['wbgt_c']=d.wbgt-d.wbgt.mean(); d['elo_c']=(d.elo_gap-d.elo_gap.mean())/100.0
    d['brk_margin']=d.brk*d.margin; d['brk_wbgt']=d.brk*d.wbgt_c; d['brk_elo']=d.brk*d.elo_c
    return d

if __name__=='__main__':
    d=build_B(10)
    nb=int(d.brk.sum()); nc=int((1-d.brk).sum()); nm=d.match_id.nunique()
    print(f"[DESIGN B] play-aligned, per-match resume | break n={nb}, control n={nc}, matches={nm}")
    def ols(f): return smf.ols("Y ~ "+f,data=d).fit(cov_type='cluster',cov_kwds={'groups':d.match_id})
    base="C(match_id) + minute + m2 + C(half) + pre_level + pre_slope + margin"
    def L(r,t):
        p=r.params[t]; s=r.bse[t]; return f"{p:+.2f} [{p-1.96*s:+.2f},{p+1.96*s:+.2f}] (p={r.pvalues[t]:.2f})"
    M0=ols(base+" + brk"); M1=ols(base+" + brk + brk_wbgt"); M2=ols(base+" + brk + brk_margin")
    M3=ols(base+" + brk + brk_elo"); M4=ols(base+" + brk + brk_margin + brk_elo + brk_wbgt")
    print("M0 base ", L(M0,'brk'))
    print("M2 +lead", L(M2,'brk'),"| xlead",L(M2,'brk_margin'))
    print("M4 full ", L(M4,'brk'),"| xlead",L(M4,'brk_margin'),"| xElo",L(M4,'brk_elo'),"| xWBGT",L(M4,'brk_wbgt'))
    def mixed(rhs): return smf.mixedlm("Y ~ "+rhs,data=d,groups=d["match_id"]).fit(method='lbfgs')
    rb="minute + m2 + C(half) + pre_level + pre_slope + margin"
    X1=mixed(rb+" + brk"); X2=mixed(rb+" + brk + brk_margin"); X3=mixed(rb+" + brk + brk_margin + brk_elo")
    print("X1 mixed", L(X1,'brk'))
    print("X3 mixed", L(X3,'brk'),"| xlead",L(X3,'brk_margin'),"| xElo",L(X3,'brk_elo'))
