"""
Consolidated, break-gap-corrected within-match case-crossover pipeline.
Key correction (reviewer comment 1): the SofaScore Attack Momentum series is indexed by nominal
match minute with the clock running through the ~3-min hydration break, so in-break minutes carry
spurious (decay-artefact) values. We therefore EXCLUDE a uniform 3-minute in-play window at each
break start c (minutes c, c+1, c+2) and measure the post-break outcome only after play resumes
(from c+3). The same 3-minute pseudo-break exclusion is applied to every control anchor, so the
treated/control contrast preserves an identical temporal structure.
Outputs: paper/figures/*.png, paper/results_ladder.txt
"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
exec(open('model_within.py').read().split('def fit(')[0])  # raw,goals,breaks,WB,mom_at,wm,wsl,sb,period,ACCITY,citym

GAP = 3                 # uniform in-play exclusion (minutes c, c+1, c+2); post-window starts at c+GAP
DROP = '15186769'       # France vs Iraq: only one break recorded (no H2 break) -> drop for 2-per-match balance

def valid_len(mid):
    """Momentum series must be consistent with nominal-minute indexing: ~90 (+trailing) for regulation,
    ~120 for extra time. Series far from these (e.g. 132, 136) carry resampling/padding artefacts that
    misalign the minute axis and the break location, so those matches are excluded."""
    if mid not in raw: return False
    L=len(raw[mid][1])
    return (80<=L<=100) or (118<=L<=128)

# oriented Elo of the dominant side
tr0=pd.DataFrame(json.load(open('data/treated_covariates.json')))
ELO=tr0.groupby('match_id')[['elo_home','elo_away']].first()
elo_h={str(k):v for k,v in ELO['elo_home'].items()}; elo_a={str(k):v for k,v in ELO['elo_away'].items()}

def gap_series(mid,c,H):
    """oriented momentum: pre-level/slope over [c-5,c-1]; post over [c+GAP, c+GAP+H-1]; None if invalid."""
    pre=wm(mid,c-5,c-1); sl=wsl(mid,c-5,c-1)
    if pre is None or sl is None: return None
    s,mo=raw[mid]; last=s+len(mo)-1
    lo, hi = c-5, c+GAP+H-1
    if lo<s or hi>last: return None
    if period(lo)!=period(hi): return None            # no half-time / period crossing
    o = 1 if pre>=0 else -1
    post=[mom_at(mid,c+GAP+k) for k in range(H)]; post=[v for v in post if v is not None]
    if not post: return None
    hs,a=sb(mid,c); dm=o*(hs-a)
    w=WB(mid); m=str(mid)
    if w is None or m not in elo_h: return None
    return dict(o=o, pre_level=o*pre, pre_slope=o*sl, margin=dm, wbgt=w,
                elo_gap=o*(elo_h[m]-elo_a[m]), Y=o*float(np.mean(post)))

def build(H):
    R=[]
    for mid,bks in breaks.items():
        if not valid_len(mid): continue                # drop corrupted-length series
        for c in bks:                                  # treated: break START minutes
            r=gap_series(mid,c,H)
            if r: R.append({'match_id':str(mid),'brk':1,'minute':c,'half':int(c>=45),**r})
    for mid,(s,mo) in raw.items():
        if not valid_len(mid): continue
        for c in range(s+5, s+len(mo)-1):              # control: candidate anchors
            if any(b-2<=c<=b+GAP+H for b in breaks.get(mid,[])): continue   # keep clear of real breaks+window
            if 43<=c<=48: continue                     # avoid half-time seam
            r=gap_series(mid,c,H)
            if r: R.append({'match_id':str(mid),'brk':0,'minute':c,'half':int(c>=45),**r})
    d=pd.DataFrame(R)
    d=d[d.match_id!=DROP].copy()
    d['m2']=d.minute**2; d['wbgt_c']=d.wbgt-d.wbgt.mean(); d['elo_c']=(d.elo_gap-d.elo_gap.mean())/100.0
    d['brk_margin']=d.brk*d.margin; d['brk_wbgt']=d.brk*d.wbgt_c; d['brk_elo']=d.brk*d.elo_c
    return d

if __name__=='__main__':
    d=build(10)
    nb=int(d.brk.sum()); nc=int((1-d.brk).sum()); nm=d.match_id.nunique()
    print(f"[gap-corrected] outcome=oriented mean momentum over [c+{GAP}, c+{GAP+9}] | break n={nb}, control n={nc}, matches={nm}")
    def ols(f): return smf.ols(f,data=d).fit(cov_type='cluster',cov_kwds={'groups':d.match_id})
    base="Y ~ C(match_id) + minute + m2 + C(half) + pre_level + pre_slope + margin"
    def L(r,t):
        p=r.params[t]; s=r.bse[t]; return f"{p:+.2f} [{p-1.96*s:+.2f},{p+1.96*s:+.2f}] (p={r.pvalues[t]:.2f})"
    M0=ols(base+" + brk"); M1=ols(base+" + brk + brk_wbgt"); M2=ols(base+" + brk + brk_margin")
    M3=ols(base+" + brk + brk_elo"); M4=ols(base+" + brk + brk_margin + brk_elo + brk_wbgt")
    print("M0 base     ", L(M0,'brk'))
    print("M1 +heat    ", L(M1,'brk'),"| xWBGT",L(M1,'brk_wbgt'))
    print("M2 +lead    ", L(M2,'brk'),"| xlead",L(M2,'brk_margin'))
    print("M3 +elo     ", L(M3,'brk'),"| xElo",L(M3,'brk_elo'))
    print("M4 full     ", L(M4,'brk'),"| xlead",L(M4,'brk_margin'),"| xElo",L(M4,'brk_elo'))
    def mixed(rhs): return smf.mixedlm("Y ~ "+rhs,data=d,groups=d["match_id"]).fit(method='lbfgs')
    rb="minute + m2 + C(half) + pre_level + pre_slope + margin"
    X1=mixed(rb+" + brk"); X2=mixed(rb+" + brk + brk_margin"); X3=mixed(rb+" + brk + brk_margin + brk_elo")
    print("X1 mixed    ", L(X1,'brk'))
    print("X2 mixed+lead", L(X2,'brk'),"| xlead",L(X2,'brk_margin'))
    print("X3 mixed+lead+elo", L(X3,'brk'),"| xlead",L(X3,'brk_margin'),"| xElo",L(X3,'brk_elo'))
    with open('paper/results_ladder.txt','w') as f:
        f.write(f"gap-corrected outcome = oriented mean momentum over post-resumption window [c+{GAP}, c+{GAP+9}]\n")
        f.write(f"break events n={nb}; control anchors n={nc}; matches={nm}; uniform {GAP}-min break exclusion\n\n")
        f.write("FIXED EFFECTS (within-match, cluster-robust):\n")
        for lab,r,extra in [("M0 base",M0,[]),("M1 +heat",M1,[('brk_wbgt','xWBGT/C')]),
                            ("M2 +lead",M2,[('brk_margin','xlead')]),("M3 +elo",M3,[('brk_elo','xElo/100')]),
                            ("M4 full",M4,[('brk_margin','xlead'),('brk_elo','xElo/100'),('brk_wbgt','xWBGT/C')])]:
            f.write(f"  {lab:10} break {L(r,'brk')}"+"".join(f" ; {nm2} {L(r,c)}" for c,nm2 in extra)+"\n")
        f.write("\nMIXED EFFECTS (random match intercept):\n")
        for lab,r,extra in [("X1 main",X1,[]),("X2 +lead",X2,[('brk_margin','xlead')]),
                            ("X3 +lead+elo",X3,[('brk_margin','xlead'),('brk_elo','xElo/100')])]:
            f.write(f"  {lab:12} break {L(r,'brk')}"+"".join(f" ; {nm2} {L(r,c)}" for c,nm2 in extra)+"\n")
    print("\nwrote paper/results_ladder.txt")
