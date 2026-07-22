import json, numpy as np, warnings; warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
exec(open('analysis_gap.py').read().split('if __name__')[0])   # loaders, valid_len, DROP, GAP
END={}
for m in json.load(open('data/wc2026_group_momentum.json')):
    for b in m.get('breaks',[]):
        if 'start' in b and 'end' in b:
            w=b['end']-b['start']; END[(m['id'],b['start'])]=b['end'] if 2<=w<=4 else b['start']+3
def resume(mid,s): return END.get((mid,s), s+3)
plt.rcParams.update({'font.family':'serif','font.size':10.5,'axes.spines.top':False,'axes.spines.right':False,
    'figure.dpi':140,'axes.grid':True,'grid.alpha':0.25,'legend.frameon':False})
RED='#c0392b'; BLUE='#2f6db5'; INK='#1f2430'
def om(mid,c,k,o): v=mom_at(mid,c+k); return o*v if v is not None else np.nan
def o_of(mid,c):
    p=wm(mid,c-5,c-1); return None if p is None else (1 if p>=0 else -1)
def okp(mid,c,lo,hi):
    s,mo=raw[mid]; last=s+len(mo)-1; return c+lo>=s and c+hi<=last and period(c+lo)==period(c+hi)
TR=[(m,c) for m,bks in breaks.items() if valid_len(m) and str(m)!=DROP for c in bks]
CT=[(m,c) for m,(s,mo) in raw.items() if valid_len(m) and str(m)!=DROP
    for c in range(s+5,s+len(mo)-16)
    if not any(b-2<=c<=b+GAP+15 for b in breaks.get(m,[])) and not (43<=c<=48)]
def mci(M): M=np.array(M); m=np.nanmean(M,0); se=np.nanstd(M,0)/np.sqrt(np.sum(np.isfinite(M),0)); return m,m-1.96*se,m+1.96*se

fig,ax=plt.subplots(1,2,figsize=(11,4.4),sharey=True)
# Panel A: clock-aligned (blank in-break 0,1,2)
K=np.arange(-5,16)
def clockcurve(anchors):
    R=[]
    for m,c in anchors:
        o=o_of(m,c)
        if o is None or not okp(m,c,-5,15): continue
        row=[]
        for k in K:
            if 0<=k<GAP: row.append(np.nan); continue
            row.append(om(m,c,k,o))
        R.append(row)
    return R
Bb=clockcurve(TR); Cc=clockcurve(CT)
mb,lb,hb=mci(Bb); mc,lc,hc=mci(Cc)
a=ax[0]; a.axvspan(-0.4,GAP-0.6,color='0.5',alpha=.28,hatch='//',ec='none'); a.axhline(0,color=INK,lw=.7)
a.plot(K,mb,color=RED,lw=1.7,marker='o',ms=3,label=f'break (n={len(Bb)})'); a.fill_between(K,lb,hb,color=RED,alpha=.13)
a.plot(K,mc,color=BLUE,lw=1.7,marker='s',ms=3,label=f'control (n={len(Cc)})'); a.fill_between(K,lc,hc,color=BLUE,alpha=.12)
a.set_title('(a) Design A: clock-aligned'); a.set_xlabel('Minutes relative to break start'); a.set_ylabel('Sign-adjusted momentum (dominant side)'); a.legend(loc='upper right',fontsize=8.5)
# Panel B: play-aligned
POST=np.arange(1,16); PRE=np.arange(-5,0)
def treatedB():
    R=[]
    for m,c in TR:
        o=o_of(m,c); e=resume(m,c)
        if o is None or not okp(m,c,-5,(e-c)+15): continue
        R.append([om(m,c,k,o) for k in PRE]+[om(m,e,k-1,o) for k in POST])
    return R
def controlB():
    R=[]
    for m,c in CT:
        o=o_of(m,c)
        if o is None or not okp(m,c,-5,15): continue
        R.append([om(m,c,k,o) for k in PRE]+[om(m,c,k,o) for k in POST])
    return R
Tb=treatedB(); Cb=controlB(); X=np.concatenate([PRE,POST])
mt,lt,ht=mci(Tb); mc2,lc2,hc2=mci(Cb)
b=ax[1]; b.axvspan(-0.5,0.5,color='0.6',alpha=.25,hatch='//',ec='none'); b.axhline(0,color=INK,lw=.7)
b.plot(X[:5],mt[:5],color=RED,lw=1.7,marker='o',ms=3); b.plot(X[5:],mt[5:],color=RED,lw=1.7,marker='o',ms=3,label=f'break (n={len(Tb)})')
b.fill_between(X[:5],lt[:5],ht[:5],color=RED,alpha=.13); b.fill_between(X[5:],lt[5:],ht[5:],color=RED,alpha=.13)
b.plot(X[:5],mc2[:5],color=BLUE,lw=1.7,marker='s',ms=3); b.plot(X[5:],mc2[5:],color=BLUE,lw=1.7,marker='s',ms=3,label=f'control (n={len(Cb)})')
b.fill_between(X[:5],lc2[:5],hc2[:5],color=BLUE,alpha=.12); b.fill_between(X[5:],lc2[5:],hc2[5:],color=BLUE,alpha=.12)
b.set_title('(b) Design B: play-aligned (break removed)'); b.set_xlabel('Play-time relative to break'); b.legend(loc='upper right',fontsize=8.5)
fig.tight_layout(); fig.savefig('paper/figures/fig_AB.png',bbox_inches='tight'); plt.close(fig)
print('fig_AB done; A post+3..+7 brk %.1f ctrl %.1f | B play+1..+3 brk %s ctrl %s'%(
   np.nanmean(mb[8:13]),np.nanmean(mc[8:13]),[round(x,1) for x in mt[5:8]],[round(x,1) for x in mc2[5:8]]))
