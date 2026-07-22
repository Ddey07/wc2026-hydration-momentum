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
def line(m, elo=None):
    b=m.params; V=m.cov_params(); mg=np.linspace(-3,3,121)
    val=b['brk']+b['brk_margin']*mg + (b['brk_elo']*elo if elo is not None else 0.0)
    var=V.loc['brk','brk']+mg**2*V.loc['brk_margin','brk_margin']+2*mg*V.loc['brk','brk_margin']
    return mg,val,1.96*np.sqrt(var)
fig,ax=plt.subplots(figsize=(8.0,4.7))
mg,v,e=line(X2)
ax.plot(mg,v,color=BLUE,lw=2,label='Break $\\times$ lead model (averaged over team strength)')
ax.fill_between(mg,v-e,v+e,color=BLUE,alpha=.15)
mg3,v3,e3=line(X3,elo=0.0)
ax.plot(mg3,v3,color=RED,lw=1.8,ls='--',label='Lead $+$ strength model, at average strength')
ax.axhline(0,color=INK,lw=1.0)
ax.set_xlabel('Oriented goal margin of the pre-break dominant side (negative $=$ behind, positive $=$ ahead)')
ax.set_ylabel('Implied break effect (sign-adjusted momentum points)')
ax.set_title('Break effect declines with the size of the lead')
ax.set_xticks(range(-3,4))
# data support: histogram of break-event margins along the bottom
t=d[d.brk==1]; import numpy as np
counts,edges=np.histogram(t.margin,bins=np.arange(-3.5,4.5,1))
y0=ax.get_ylim()[0]
for c,left in zip(counts,edges[:-1]):
    ax.bar(left+0.5,0.9*abs(y0)*c/counts.max(),bottom=y0,width=0.8,color=MUT,alpha=.20,zorder=0)
ax.legend(loc='upper right',fontsize=8.5,frameon=False)
ax.annotate('for scale: pre-break level $\\approx$ +20; natural fade $\\approx$ $-$12',
            xy=(0.015,0.04),xycoords='axes fraction',fontsize=8,color=MUT)
fig.tight_layout(); fig.savefig('paper/figures/fig4_effect_by_margin.png',bbox_inches='tight'); plt.close(fig)
print('continuous effect plot written')
for m in [-1,0,1,2]:
    b=X2.params; print('  X2 effect at margin %+d: %+.2f'%(m,b['brk']+b['brk_margin']*m))
