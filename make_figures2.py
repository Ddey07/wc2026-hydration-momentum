"""Gap-corrected figures + referent-sensitivity table + Table 1 descriptives."""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')
exec(open('analysis_gap.py').read().split("if __name__")[0])   # loaders + build + GAP + gap_series + elo
plt.rcParams.update({'font.family':'serif','font.size':11,'axes.titlesize':12,'axes.labelsize':11,
    'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'axes.grid':True,
    'grid.alpha':0.25,'grid.linewidth':0.6,'legend.frameon':False})
BLUE='#2f6db5'; RED='#c0392b'; INK='#1f2430'; MUT='#6b7280'; GOLD='#c98a1a'; GREEN='#2e7d5b'; FIG='paper/figures'

# ============================ FIG 1: sign-adjusted outcome WITH break gap ============================
mid=12813017; s,mo=raw[mid]; bk=[b for b in breaks[mid] if b<45][0]
mins=np.array(range(s,s+len(mo)),dtype=float); yraw=np.array(mo,dtype=float)
o=1 if wm(mid,bk-5,bk-1)>=0 else -1
# blank the in-play break window [bk, bk+GAP-1] so the curve shows a gap
def blанk(arr):
    a=arr.copy()
    for k in range(GAP):
        idx=np.where(mins==bk+k)[0]
        if len(idx): a[idx]=np.nan
    return a
yraw_g=blанk(yraw); yor=o*yraw; yor_g=blанk(yor)
fig,ax=plt.subplots(1,2,figsize=(10.4,3.9))
a=ax[0]; a.axhline(0,color=INK,lw=.8)
a.fill_between(mins,yraw_g,0,where=yraw_g>=0,color=BLUE,alpha=.35,linewidth=0)
a.fill_between(mins,yraw_g,0,where=yraw_g<0,color=RED,alpha=.35,linewidth=0)
a.plot(mins,yraw_g,color=INK,lw=1.0)
a.axvspan(bk-5,bk-1,color=GOLD,alpha=.20); a.axvspan(bk,bk+GAP-1,color='0.5',alpha=.35,hatch='//',ec='none')
a.set_xlim(5,60); a.set_title('(a) Raw signed attack momentum'); a.set_xlabel('Match minute'); a.set_ylabel('Momentum (home + / away $-$)')
a.text(bk-3,a.get_ylim()[1]*.92,'pre-break\nwindow',ha='center',va='top',fontsize=8.3,color=GOLD)
a.text(bk+0.6,a.get_ylim()[0]*.9,'break\n(no play)',ha='center',va='bottom',fontsize=8.0,color='0.3')
a.text(12,a.get_ylim()[1]*.7,'HOME',color=BLUE,fontsize=9,weight='bold'); a.text(12,a.get_ylim()[0]*.7,'AWAY',color=RED,fontsize=9,weight='bold')
b=ax[1]; b.axhline(0,color=INK,lw=.8)
b.fill_between(mins,yor_g,0,where=yor_g>=0,color=GREEN,alpha=.35,linewidth=0)
b.fill_between(mins,yor_g,0,where=yor_g<0,color=MUT,alpha=.25,linewidth=0)
b.plot(mins,yor_g,color=INK,lw=1.0)
b.axvspan(bk-5,bk-1,color=GOLD,alpha=.20); b.axvspan(bk,bk+GAP-1,color='0.5',alpha=.35,hatch='//',ec='none')
preL=o*wm(mid,bk-5,bk-1); postL=o*float(np.mean([mom_at(mid,bk+GAP+k) for k in range(10)]))
b.plot([bk-3],[preL],'o',color=GREEN,ms=5); b.plot([bk+GAP+4.5],[postL],'o',color=GREEN,ms=5)
b.annotate('',xy=(bk+GAP+4.5,postL),xytext=(bk-3,preL),arrowprops=dict(arrowstyle='->',color=INK,lw=1.1))
b.text(bk+GAP+0.5,(preL+postL)/2+5,'post-resumption\nmomentum',fontsize=8.0,color=INK)
b.set_xlim(5,60); b.set_title('(b) Sign-adjusted (dominant-side) momentum $Y_t=o\\cdot M_t$')
b.set_xlabel('Match minute'); b.set_ylabel('Momentum toward pre-break dominant side')
b.text(12,b.get_ylim()[1]*.7,'DOMINANT side (+)',color=GREEN,fontsize=8.5,weight='bold')
fig.tight_layout(); fig.savefig(f'{FIG}/fig1_orientation.png',bbox_inches='tight'); plt.close(fig)
print('fig1 (gap) done; o=%d preL=%.1f postL=%.1f'%(o,preL,postL))

# ============================ FIG 2: regression-to-mean WITH break gap ============================
def oriented(mid,c,lo=-5,hi=15):
    pre=wm(mid,c-5,c-1)
    if pre is None: return None
    o=1 if pre>=0 else -1; s,mo=raw[mid]; last=s+len(mo)-1
    if c+lo<s or c+hi>last or period(c+lo)!=period(c+hi): return None
    out=[]
    for k in range(lo,hi+1):
        if 0<=k<GAP: out.append(np.nan); continue         # blank in-break minutes
        v=mom_at(mid,c+k); out.append(o*v if v is not None else np.nan)
    return np.array(out)
K=np.arange(-5,16); Br=[]; Ct=[]
for mid,bks in breaks.items():
    if str(mid)==DROP or not valid_len(mid): continue
    for c in bks:
        r=oriented(mid,c); Br.append(r) if r is not None else None
for mid,(s,mo) in raw.items():
    if str(mid)==DROP or not valid_len(mid): continue
    for c in range(s+5,s+len(mo)-15):
        if any(b-2<=c<=b+GAP+15 for b in breaks.get(mid,[])): continue
        if 43<=c<=48: continue
        r=oriented(mid,c); Ct.append(r) if r is not None else None
Br=np.vstack(Br); Ct=np.vstack(Ct)
def mci(M): m=np.nanmean(M,0); se=np.nanstd(M,0)/np.sqrt(np.sum(np.isfinite(M),0)); return m,m-1.96*se,m+1.96*se
mb,lb,hb=mci(Br); mc,lc,hc=mci(Ct)
fig,ax=plt.subplots(figsize=(7.2,4.4))
ax.axvspan(-0.4,GAP-0.6,color='0.5',alpha=.30,hatch='//',ec='none')
ax.axhline(0,color=INK,lw=.7)
ax.plot(K,mb,color=RED,lw=1.8,label=f'break minutes (n={Br.shape[0]})',marker='o',ms=3)
ax.fill_between(K,lb,hb,color=RED,alpha=.15)
ax.plot(K,mc,color=BLUE,lw=1.8,label=f'non-break control anchors (n={Ct.shape[0]})',marker='s',ms=3)
ax.fill_between(K,lc,hc,color=BLUE,alpha=.12)
ax.set_xlabel('Minutes relative to break start (in-break minutes blanked)'); ax.set_ylabel('Sign-adjusted momentum (dominant side)')
ax.set_title('The break neither creates nor prevents the fade: treated and control decay alike')
ax.text((GAP-1)/2-0.2,ax.get_ylim()[1]*.96,'break\n(no play)',fontsize=8,va='top',ha='center',color='0.3')
ax.legend(loc='upper right')
fig.tight_layout(); fig.savefig(f'{FIG}/fig2_regression_to_mean.png',bbox_inches='tight'); plt.close(fig)
print('fig2 (gap) done; pre(-5..-1) brk=%.1f ctrl=%.1f | post(+3..+7) brk=%.1f ctrl=%.1f'%(
      np.nanmean(mb[0:5]),np.nanmean(mc[0:5]),np.nanmean(mb[8:13]),np.nanmean(mc[8:13])))

# ============================ FIG 3 (was fig4): break-minute windows ============================
bm=[b for mid,bks in breaks.items() if str(mid)!=DROP for b in bks]
fig,ax=plt.subplots(figsize=(7.2,3.4))
ax.hist([b for b in bm if b<45],bins=range(18,32),color=GREEN,alpha=.75,label='first-half breaks')
ax.hist([b for b in bm if b>=45],bins=range(62,78),color=GOLD,alpha=.75,label='second-half breaks')
ax.set_xlabel('Break start minute'); ax.set_ylabel('Number of break events')
ax.set_title('Breaks occur only in two narrow windows ($\\approx$23$^\\prime$ and $\\approx$68$^\\prime$)')
ax.legend()
fig.tight_layout(); fig.savefig(f'{FIG}/fig3_break_minutes.png',bbox_inches='tight'); plt.close(fig)
print('fig3 (break minutes) done')

# ============================ Referent / time-trend sensitivity table ============================
d=build(10); d['brk_margin']=d.brk*d.margin
def fit(dd,g):
    m=smf.ols(f"Y ~ {g} + C(half) + pre_level + pre_slope + margin + brk + brk_margin",
              data=dd).fit(cov_type='cluster',cov_kwds={'groups':dd.match_id})
    ci=lambda t:(m.params[t],m.params[t]-1.96*m.bse[t],m.params[t]+1.96*m.bse[t])
    return ci('brk'),ci('brk_margin'),int((1-dd.brk).sum())
rows=[]
for lab,g in [("linear","minute"),("quadratic","minute + m2"),("cubic","minute + m2 + I(minute**3)"),("per-minute dummies","C(minute)")]:
    b,gm,ncc=fit(d,g); rows.append(("A",lab,b,gm,ncc))
def band(dd,a,bb,cc,e):
    keep=((dd.brk==0)&(((dd.half==0)&dd.minute.between(a,bb))|((dd.half==1)&dd.minute.between(cc,e))))
    return dd[(dd.brk==1)|keep].copy()
for lab,(a,bb,cc,e) in [("adjacent 15-32 | 60-77",(15,32,60,77)),("mid 11-40 | 56-85",(11,40,56,85)),
                        ("far 6-15 | 73-78",(6,15,73,78)),("all eligible",(0,44,45,120))]:
    dd=band(d,a,bb,cc,e); b,gm,ncc=fit(dd,"minute + m2"); rows.append(("B",lab,b,gm,ncc))
with open('paper/referent_table.txt','w') as f:
    for grp,lab,b,gm,ncc in rows:
        f.write(f"{grp} {lab:26} beta {b[0]:+.2f}[{b[1]:+.2f},{b[2]:+.2f}]  gamma {gm[0]:+.2f}[{gm[1]:+.2f},{gm[2]:+.2f}]  nctrl={ncc}\n")
print('referent table written'); print(open('paper/referent_table.txt').read())
