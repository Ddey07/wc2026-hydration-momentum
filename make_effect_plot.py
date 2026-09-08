import numpy as np, statsmodels.formula.api as smf, warnings
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')
exec(open('analysis_gap.py').read().split('if __name__')[0])
plt.rcParams.update({'font.family':'serif','font.size':11,'axes.spines.top':False,'axes.spines.right':False,
    'figure.dpi':140,'axes.grid':True,'grid.alpha':0.25})
INK='#1f2430'; BLUE='#2f6db5'; RED='#c0392b'; MUT='#6b7280'
d=build(10); rb='minute + m2 + C(half) + pre_level + pre_slope + margin'
X2=smf.mixedlm('Y ~ '+rb+' + brk + brk_margin',data=d,groups=d['match_id']).fit(method='lbfgs')
X3=smf.mixedlm('Y ~ '+rb+' + brk + brk_margin + brk_elo',data=d,groups=d['match_id']).fit(method='lbfgs')
elo_mean=d.elo_gap.mean()

fig,ax=plt.subplots(1,2,figsize=(11.2,4.5))

# ---- Panel (a): effect vs oriented goal margin ----
a=ax[0]
def line_margin(m,elo_c=None):
    b=m.params; V=m.cov_params(); mg=np.linspace(-3,3,121)
    val=b['brk']+b['brk_margin']*mg + (b['brk_elo']*elo_c if elo_c is not None else 0.0)
    var=V.loc['brk','brk']+mg**2*V.loc['brk_margin','brk_margin']+2*mg*V.loc['brk','brk_margin']
    return mg,val,1.96*np.sqrt(var)
mg,v,e=line_margin(X2)
a.plot(mg,v,color=BLUE,lw=2,label='Break $\\times$ lead (averaged over strength)')
a.fill_between(mg,v-e,v+e,color=BLUE,alpha=.15)
mg3,v3,e3=line_margin(X3,elo_c=0.0)
a.plot(mg3,v3,color=RED,lw=1.8,ls='--',label='Lead $+$ strength model, at average strength')
a.axhline(0,color=INK,lw=1.0)
a.set_xlabel('Oriented goal margin (negative $=$ behind, positive $=$ ahead)')
a.set_ylabel('Implied break effect (momentum points)')
a.set_title('(a) Effect by scoreline')
a.set_xticks(range(-3,4))
t=d[d.brk==1]; counts,edges=np.histogram(t.margin,bins=np.arange(-3.5,4.5,1)); y0=a.get_ylim()[0]
for c,left in zip(counts,edges[:-1]):
    a.bar(left+0.5,0.9*abs(y0)*c/counts.max(),bottom=y0,width=0.8,color=MUT,alpha=.20,zorder=0)
a.legend(loc='upper right',fontsize=8,frameon=False)

# ---- Panel (b): effect vs oriented Elo gap (margin held at level) ----
b=ax[1]
bb=X3.params; V=X3.cov_params()
elo=np.linspace(-300,500,161); ec=(elo-elo_mean)/100.0
val=bb['brk']+bb['brk_elo']*ec
var=V.loc['brk','brk']+ec**2*V.loc['brk_elo','brk_elo']+2*ec*V.loc['brk','brk_elo']
err=1.96*np.sqrt(var)
b.plot(elo,val,color=BLUE,lw=2,label='Break $\\times$ strength (at level scoreline)')
b.fill_between(elo,val-err,val+err,color=BLUE,alpha=.15)
b.axhline(0,color=INK,lw=1.0)
b.set_xlabel('Oriented Elo advantage of dominant side (points)')
b.set_ylabel('Implied break effect (momentum points)')
b.set_title('(b) Effect by team strength')
te=d[d.brk==1]; counts2,edges2=np.histogram(te.elo_gap,bins=np.linspace(-300,500,9)); y0b=b.get_ylim()[0]
for c,left,right in zip(counts2,edges2[:-1],edges2[1:]):
    b.bar((left+right)/2,0.9*abs(y0b)*c/max(counts2.max(),1),bottom=y0b,width=(right-left)*0.9,color=MUT,alpha=.20,zorder=0)
b.legend(loc='upper right',fontsize=8,frameon=False)

fig.tight_layout()
fig.savefig('paper/figures/fig4_effect_by_margin.png',bbox_inches='tight'); plt.close(fig)
print('two-panel effect plot written')
# report Elo effect at illustrative advantages
for E in [-200,0,200,400]:
    ec=(E-elo_mean)/100.0; val=bb['brk']+bb['brk_elo']*ec
    se=np.sqrt(V.loc['brk','brk']+ec**2*V.loc['brk_elo','brk_elo']+2*ec*V.loc['brk','brk_elo'])
    print('  Elo adv %+4d: effect %+.2f [%+.2f,%+.2f]'%(E,val,val-1.96*se,val+1.96*se))
