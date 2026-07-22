import numpy as np, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
exec(open('analysis_gap.py').read().split('if __name__')[0])
d=build(10)
base='C(match_id) + minute + m2 + C(half) + pre_level + pre_slope + margin'
specs={
 'Baseline':                base+' + brk',
 'Break$\\times$lead':       base+' + brk + brk_margin',
 'Break$\\times$lead$+$Elo':  base+' + brk + brk_margin + brk_elo',
 'Full':                    base+' + brk + brk_margin + brk_elo + brk_wbgt',
}
def fit(f): return smf.ols('Y ~ '+f,data=d).fit(cov_type='cluster',cov_kwds={'groups':d.match_id})
fits={k:fit(v) for k,v in specs.items()}
rowmap=[('Minute','minute'),('Minute$^2$','m2'),('Second half','C(half)[T.1]'),
 ('Pre-break level','pre_level'),('Pre-break slope','pre_slope'),('Score margin','margin'),
 ('Break','brk'),('Break $\\times$ lead','brk_margin'),
 ('Break $\\times$ Elo/100','brk_elo'),('Break $\\times$ heat/$^\\circ$C','brk_wbgt')]
def cell(f,key):
    if key not in f.params.index: return '--'
    return '$%+.2f$ (%.2f)'%(f.params[key],f.bse[key])
print(' | '.join(['Term']+list(specs.keys())))
for lab,key in rowmap:
    print(' | '.join([lab]+[cell(fits[k],key) for k in specs]))
with open('paper/coef_rows.tex','w') as fo:
    for lab,key in rowmap:
        fo.write(lab+' & '+' & '.join(cell(fits[k],key) for k in specs)+' \\\\\n')
    fo.write('\\midrule\n')
    fo.write('Match fixed effects & Yes & Yes & Yes & Yes \\\\\n')
    fo.write('Within $R^2$ & '+' & '.join('%.3f'%fits[k].rsquared for k in specs)+' \\\\\n')
print('\nwrote paper/coef_rows.tex ; break events=%d, control anchors=%d, matches=%d'%(int(d.brk.sum()),int((1-d.brk).sum()),d.match_id.nunique()))
