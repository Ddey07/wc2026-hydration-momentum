import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
plt.rcParams.update({'font.family':'serif','font.size':10.5})
GOLD='#c98a1a'; GREY='0.6'; GREEN='#2e7d5b'; BLUE='#2f6db5'; INK='#1f2430'
fig,ax=plt.subplots(figsize=(9.2,4.3)); ax.set_xlim(-6,15); ax.set_ylim(0,3.4); ax.axis('off')
def band(x0,x1,y,color,alpha,label=None,hatch=None,ec='none'):
    ax.add_patch(Rectangle((x0,y-0.28),x1-x0,0.56,facecolor=color,alpha=alpha,hatch=hatch,edgecolor=ec,lw=0.8))
def lab(x,y,t,c=INK,fs=9,w='normal'): ax.text(x,y,t,ha='center',va='center',fontsize=fs,color=c,weight=w)
def rowlab(y,t): ax.text(-6.3,y,t,ha='right',va='center',fontsize=9.5,weight='bold')
# axis
ax.annotate('',xy=(15,0.25),xytext=(-6,0.25),arrowprops=dict(arrowstyle='->',color=INK,lw=1))
for m in range(-5,15,1): ax.plot([m,m],[0.2,0.3],color=INK,lw=.6)
for m in [-5,0,3,12]: ax.text(m,0.02,{-5:'$c-5$',0:'$c$',3:'$c+3$',12:'$c+12$'}[m],ha='center',fontsize=8,color=INK)
ax.text(14.5,0.02,'minutes',ha='right',fontsize=8,color=INK,style='italic')
# Row 1: break event (same under both designs)
y=2.8; rowlab(y,'Break event')
band(-5,-0.05,y,GOLD,.35); lab(-2.5,y,'pre-break',GOLD,8.5)
band(0,3,y,GREY,.45,hatch='//'); lab(1.5,y+0.02,'break',INK,8,w='bold')
band(3,12.05,y,GREEN,.35); lab(7.5,y,'post-resumption outcome',GREEN,8.5)
# Row 2: control under clock-aligned (Design A)
y=1.9; rowlab(y,'Control\n(Design A: clock)')
band(-5,-0.05,y,GOLD,.35); lab(-2.5,y,'pre',GOLD,8.5)
band(0,3,y,'0.85',.9,hatch='..',ec='0.5'); lab(1.5,y,'skipped',INK,7.5,w='bold')
band(3,12.05,y,BLUE,.30); lab(7.5,y,'outcome $[c{+}3,c{+}12]$',BLUE,8.5)
# Row 3: control under play-aligned (Design B)
y=1.0; rowlab(y,'Control\n(Design B: play)')
band(-5,-0.05,y,GOLD,.35); lab(-2.5,y,'pre',GOLD,8.5)
band(1,11.05,y,BLUE,.30); lab(6,y,'outcome $[c{+}1,c{+}10]$ (immediate)',BLUE,8.5)
# connecting note
ax.text(4.5,3.35,'The two designs differ only in the control window: clock-aligned skips three minutes to match the break;\nplay-aligned uses the immediate continuation, treating the break as removed (dead) time.',
        ha='center',va='top',fontsize=8.2,color=INK)
fig.tight_layout(); fig.savefig('paper/figures/fig_designs.png',bbox_inches='tight',dpi=150); plt.close(fig)
print('schematic done')
