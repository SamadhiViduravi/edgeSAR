# Fig. 3 of the EdgeSAR paper (v2.16): missed incidents at medium load against the number of Q4 labels
# used for retraining, with the four reference levels labeled with their values.
# Usage: python3 fig3_labels_v216.py OUTDIR   -> OUTDIR/fig3_labels.pdf and OUTDIR/edgesar_fig_3.png (600 dpi)
#
# Numbers (missed share, %, set A or development, medium load, prefix position):
#   fresh retrained, mean of five label draws, with 95% episode-bootstrap CI:
#     fresh_confirmation/RESULTS.md (primary analysis table):
#     100 labels 9.63 (9.02 to 10.24); 300 labels 8.05 (7.44 to 8.65); 1,000 labels 7.16 (6.49 to 7.83)
#   fresh references: FP16 classifier 6.84, label-free map 6.91 (fresh_confirmation/RESULTS.md; paper Table 5)
#   development retrained, one label draw per fold:
#     development_study/practical_advantage/out_trace/TRACE_RESULTS.md: 100 labels 7.59, 300 labels 6.83;
#     all fitting labels (about 520) 6.56 (paper Table 1)
#   development references: FP16 classifier 5.98, label-free map 6.41 (paper Table 1)
import sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 9, 'pdf.fonttype': 42,
                     'axes.linewidth': 0.8, 'xtick.major.width': 0.8, 'ytick.major.width': 0.8})
NAVY, TEAL, GRAY = '#1E3A8A', '#0F766E', '#374151'

dev_x, dev_y = [100, 300, 520], [7.59, 6.83, 6.56]
fr_x, fr_y = [100, 300, 1000], [9.63, 8.05, 7.16]
fr_lo, fr_hi = [9.02, 7.44, 6.49], [10.24, 8.65, 7.83]
FR_FP16, FR_MAP, DEV_FP16, DEV_MAP = 6.84, 6.91, 5.98, 6.41

fig = plt.figure(figsize=(239.672 / 72, 189.325 / 72))
ax = fig.add_axes([38.643 / 239.672, 36.206 / 189.325, 191.077 / 239.672, 131.558 / 189.325])
ax.set_xscale('log')
ax.grid(True, color='#E5E7EB', linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)

ax.axhline(FR_MAP, color=TEAL, lw=1.0, zorder=2)
ax.axhline(FR_FP16, color=GRAY, lw=1.0, zorder=2)
ax.axhline(DEV_MAP, color=TEAL, lw=1.2, ls=':', zorder=2)
ax.axhline(DEV_FP16, color=GRAY, lw=0.8, ls=':', zorder=2)

ax.plot(dev_x, dev_y, ls=':', lw=1.2, color=NAVY, marker='o', ms=3.5, zorder=3, label='Q4 retrained (development)')
yerr = [[y - lo for y, lo in zip(fr_y, fr_lo)], [hi - y for y, hi in zip(fr_y, fr_hi)]]
ax.errorbar(fr_x, fr_y, yerr=yerr, ls='-', lw=1.2, color=NAVY, marker='o', ms=3.5, capsize=2, elinewidth=0.8,
            capthick=0.8, zorder=3, label='Q4 retrained (fresh)')

lab = dict(fontsize=6.3, ha='left', zorder=4)
# the upper line of each pair is labeled above it, the lower one below it
ax.text(390, FR_MAP + 0.06, 'fresh: map %.2f%%' % FR_MAP, color=TEAL, va='bottom', **lab)
ax.text(106, FR_FP16 - 0.07, 'fresh: FP16 %.2f%%' % FR_FP16, color=GRAY, va='top', **lab)
ax.text(122, DEV_MAP - 0.07, 'development: map %.2f%%' % DEV_MAP, color=TEAL, va='top', **lab)
ax.text(122, DEV_FP16 - 0.07, 'development: FP16 %.2f%%' % DEV_FP16, color=GRAY, va='top', **lab)

ax.set_xticks([100, 300, 520, 1000])
ax.set_xticklabels(['100', '300', '520', '1000'])
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_xlim(100 / 10 ** 0.05, 1000 * 10 ** 0.05)
ax.set_ylim(5.62, 10.453)
ax.set_yticks([6, 7, 8, 9, 10])
ax.set_xlabel('Q4 labels used for retraining (log scale)')
ax.set_ylabel('Missed incidents (%), medium load')
ax.legend(loc='upper right', fontsize=6.5, frameon=False, handlelength=2.2)
fig.savefig(os.path.join(out, 'fig3_labels.pdf'))
fig.savefig(os.path.join(out, 'edgesar_fig_3.png'), dpi=600)
print('ok')
