"""Net-xG break effect under BOTH counterfactual alignments, matching the momentum designs.
Design A (clock-aligned): outcome window [c+3, c+12] for break AND control.
Design B (play-aligned):  break over [resume, resume+9]; control over [c+1, c+10].
xG has no shots during the dead break window, so the two should agree closely."""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
exec(open('analysis_gap.py').read().split('if __name__')[0])   # raw,breaks,WB,wm,wsl,sb,period,valid_len,DROP,GAP,elo_h/elo_a
XG={int(k):v for k,v in json.load(open('data/xg_2026.json')).items()}

# per-match resume minute (as in analysis_designB.py)
END={}
for m in json.load(open('data/wc2026_group_momentum.json')):
    for b in m.get('breaks',[]):
        if 'start' in b and 'end' in b:
            w=b['end']-b['start']; END[(m['id'],b['start'])]=b['end'] if 2<=w<=4 else b['start']+3
def resume(mid,s): return END.get((str(mid),s), END.get((mid,s), s+3))

def netxg_window(mid,o,lo,hi):
    if mid not in XG: return None
    s=0.0
    for sh in XG[mid]:
        if lo <= sh['t'] <= hi: s+= sh['xg']*(1 if sh['h'] else -1)
    return o*s

def build(design):
    R=[]
    def add(mid,c,brk):
        pre=wm(mid,c-5,c-1); sl=wsl(mid,c-5,c-1)
        if pre is None or sl is None: return
        s,mo=raw[mid]; last=s+len(mo)-1
        o=1 if pre>=0 else -1
        if design=='A':
            lo,hi=c+GAP, c+GAP+9
        else:
            lo,hi=(resume(mid,c), resume(mid,c)+9) if brk else (c+1, c+10)
        if c-5<s or hi>last or period(c-5)!=period(hi): return
        y=netxg_window(mid,o,lo,hi)
        if y is None: return
        hs,a=sb(mid,c); w=WB(mid)
        if w is None: return
        R.append(dict(match_id=str(mid),brk=brk,minute=c,m2=c*c,half=int(c>=45),
                      pre_level=o*pre,pre_slope=o*sl,margin=o*(hs-a),Y=y))
    for mid,bks in breaks.items():
        if not valid_len(mid): continue
        for c in bks: add(mid,c,1)
    for mid,(s,mo) in raw.items():
        if not valid_len(mid): continue
        for c in range(s+5, s+len(mo)-1):
            if any(b-2<=c<=b+GAP+10 for b in breaks.get(mid,[])): continue
            if 43<=c<=48: continue
            add(mid,c,0)
    d=pd.DataFrame(R); d=d[d.match_id!=DROP].copy()
    return d

for design,lab in [('A','clock-aligned'),('B','play-aligned')]:
    d=build(design)
    if str(XG and True):
        d=d[d.match_id.astype(int).isin(XG.keys())].copy()
    m=smf.ols("Y ~ C(match_id) + minute + m2 + C(half) + pre_level + pre_slope + margin + brk",
              data=d).fit(cov_type='cluster',cov_kwds={'groups':d.match_id})
    b=m.params['brk']; se=m.bse['brk']; p=m.pvalues['brk']
    print(f"[{lab}] net-xG break effect = {b:+.4f}  95%CI [{b-1.96*se:+.4f}, {b+1.96*se:+.4f}]  (p={p:.2f})  "
          f"n_break={int(d.brk.sum())} n_ctrl={int((1-d.brk).sum())} matches={d.match_id.nunique()}")
