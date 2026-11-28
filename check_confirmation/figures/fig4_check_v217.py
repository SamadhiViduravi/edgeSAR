# Fig. 4 (v2.17): true mission penalty of the 39 candidates (set C1, medium load) against the
# label-free mission check, the share of changed records and the accuracy drop.
# Same data and layout as v2.15/v2.16; only the legend entry of the text baselines changed ("Text only" ->
# "Text baselines", because the TF-IDF baseline also reads incident-context tokens).
# Usage: python3 fig4_check_v217.py check_results.json outdir
import json, sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src))
rows = [r for r in d['rows'] if r['set'] == 'C1' and r['level'] == 'M']
cond = d['conditions']

plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 8, 'axes.titlesize': 8,
                     'axes.labelsize': 8, 'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
                     'legend.fontsize': 7.5, 'pdf.fonttype': 42, 'axes.linewidth': 0.6})
BLUE, GREEN, ORANGE, GREY = '#2F7FD3', '#1BA97A', '#E8642C', '#6b6b6b'

def group(arm):
    if arm in ('tfidf', 'rule'): return 'text'
    if arm == 'plp' or arm.startswith('ret'): return 'retrained'
    return 'reused'
STYLE = {'reused': dict(marker='o', color=BLUE, s=16), 'retrained': dict(marker='s', color=GREEN, s=15),
         'text': dict(marker='^', color=ORANGE, s=18)}

COLS = [('check_pp', 'Label-free mission check (pp)', 'spearman_check_pp'),
        ('flips', 'Records changed vs. old (%)', 'spearman_flips'),
        ('accuracy_drop', 'Accuracy drop vs. gold (points)', 'spearman_accuracy_drop')]
TARGETS = [('Q4_K_M', '4-bit (Q4_K_M)'), ('Q3_K_M', '3-bit (Q3_K_M)')]

def pt(t, arm, key):
    r = next(r for r in rows if r['target'] == t and r['arm'] == arm)
    return r['true_pp'], r[key]

# label placements: (text, arms to point at or None, text position in data units, ha)
LAB = {
 ('Q4_K_M', 'check_pp'): [('unchanged', None, ('rawp', 0.35, -0.15), 'left'),
                          ('TF-IDF, rules', ['tfidf', 'rule'], (-1.55, 2.9), 'left'),
                          ('map, pseudo-labels', ['alnp', 'plp'], (0.9, -1.35), 'left')],
 ('Q4_K_M', 'flips'): [('unchanged', None, ('rawp', 0.35, -0.6), 'left'),
                       ('TF-IDF, rules', ['tfidf', 'rule'], (-1.55, 25.5), 'left'),
                       ('pseudo-labels', ['plp'], (-1.55, 4.9), 'left'),
                       ('map', None, ('alnp', 0.35, 0.0), 'left')],
 ('Q4_K_M', 'accuracy_drop'): [('unchanged', None, ('rawp', 0.35, -0.8), 'left'),
                               ('map, pseudo-labels', ['alnp', 'plp'], (0.9, -6.5), 'left'),
                               ('TF-IDF, rules', None, ('tfidf', 0.75, -1.2), 'left')],
 ('Q3_K_M', 'check_pp'): [('unchanged', None, ('rawp', 0.45, -1.45), 'right'),
                          ('TF-IDF, rules', ['tfidf', 'rule'], (-2.0, 4.6), 'left'),
                          ('map, pseudo-labels', ['alnp', 'plp'], (1.6, -1.4), 'left')],
 ('Q3_K_M', 'flips'): [('unchanged', None, ('rawp', 0.45, -5.0), 'right'),
                       ('TF-IDF, rules', ['tfidf', 'rule'], (-2.0, 31.0), 'left'),
                       ('map, pseudo-labels', ['alnp', 'plp'], (1.6, 6.5), 'left')],
 ('Q3_K_M', 'accuracy_drop'): [('unchanged', None, ('rawp', 0.45, -5.2), 'right'),
                               ('map, pseudo-labels', ['alnp', 'plp'], (1.6, -9.5), 'left'),
                               ('TF-IDF, rules', None, ('tfidf', 1.1, -1.5), 'left')],
}
YLIM = {('Q4_K_M', 'check_pp'): (-2.6, 7.6), ('Q4_K_M', 'flips'): (2.5, 40), ('Q4_K_M', 'accuracy_drop'): (-19, 26),
        ('Q3_K_M', 'check_pp'): (-2.6, 13.6), ('Q3_K_M', 'flips'): (2.5, 63), ('Q3_K_M', 'accuracy_drop'): (-22, 46)}
XLIM = {'Q4_K_M': (-2.0, 6.0), 'Q3_K_M': (-2.4, 12.5)}

fig, axes = plt.subplots(2, 3, figsize=(6.9, 4.2))
for i, (t, tname) in enumerate(TARGETS):
    rr = [r for r in rows if r['target'] == t]
    c = cond[t + ' C1 M']
    for j, (key, title, skey) in enumerate(COLS):
        ax = axes[i][j]
        for g in ('reused', 'retrained', 'text'):
            xs = [r['true_pp'] for r in rr if group(r['arm']) == g]
            ys = [r[key] for r in rr if group(r['arm']) == g]
            ax.scatter(xs, ys, edgecolors='white', linewidths=0.4, zorder=3, **STYLE[g])
        ax.set_xlim(*XLIM[t]); ax.set_ylim(*YLIM[(t, key)])
        if key == 'check_pp':
            lo, hi = -1.6, XLIM[t][1] - 0.2
            ax.plot([lo, hi], [lo, hi], ls='--', lw=0.8, color=GREY, zorder=1)
            ex = 3.9 if t == 'Q4_K_M' else 7.6
            ax.text(ex, ex - (1.65 if t == 'Q4_K_M' else 2.1), 'equal values', color=GREY, fontsize=7.5, ha='left')
        for text, arms, pos, ha in LAB[(t, key)]:
            if isinstance(pos[0], str):
                x0, y0 = pt(t, pos[0], key)
                ax.text(x0 + pos[1], y0 + pos[2], text, fontsize=7.5, ha=ha, va='center', zorder=4)
            else:
                ax.text(pos[0], pos[1], text, fontsize=7.5, ha=ha, va='center', zorder=4)
            if arms:
                xs = [pt(t, a, key)[0] for a in arms]; ys = [pt(t, a, key)[1] for a in arms]
                tx, ty = sum(xs) / len(xs), sum(ys) / len(ys)
                sx = pos[0] + (0.15 if ha == 'left' else -0.15)
                sy = pos[1] + (0.6 if pos[1] < ty else -0.6) * (YLIM[(t, key)][1] - YLIM[(t, key)][0]) / 20
                ax.annotate('', xy=(tx, ty), xytext=(sx, sy),
                            arrowprops=dict(arrowstyle='-', lw=0.6, color=GREY, shrinkA=0, shrinkB=3), zorder=2)
        ax.text(0.03, 0.96, 'Spearman %.2f' % c[skey], transform=ax.transAxes, ha='left', va='top', fontsize=7.5,
                bbox=dict(boxstyle='square,pad=0.25', fc='white', ec='#bdbdbd', lw=0.5), zorder=5)
        ax.grid(True, color='#e6e6e6', lw=0.5, zorder=0)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        ax.tick_params(length=2.5, width=0.5, pad=2)
        if i == 0: ax.set_title(title, pad=4)
        if i == 1: ax.set_xlabel('True penalty (pp)', labelpad=2)
        if j == 0: ax.set_ylabel(tname, labelpad=2)

handles = [Line2D([], [], ls='', marker='o', color=BLUE, ms=4.5, label='FP16 classifier reused (unchanged, recentered, map, CORAL, Procrustes, recalibrated)'),
           Line2D([], [], ls='', marker='s', color=GREEN, ms=4.2, label='Retrained on the quantized vectors (labels or pseudo-labels)'),
           Line2D([], [], ls='', marker='^', color=ORANGE, ms=4.8, label="Text baselines (TF-IDF, rules)")]
leg1 = fig.legend(handles=handles[:1], loc='lower center', ncol=1, frameon=False, bbox_to_anchor=(0.5, 0.035),
                  handletextpad=0.3, borderaxespad=0.1)
fig.legend(handles=handles[1:], loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.01),
           handletextpad=0.3, columnspacing=1.6, borderaxespad=0.1)
fig.add_artist(leg1)
fig.tight_layout(rect=(0, 0.095, 1, 1), h_pad=0.9, w_pad=1.0)
os.makedirs(out, exist_ok=True)
fig.savefig(os.path.join(out, 'fig4_check.pdf'))
fig.savefig(os.path.join(out, 'edgesar_fig_4.png'), dpi=600)
print('saved', fig.get_size_inches())
