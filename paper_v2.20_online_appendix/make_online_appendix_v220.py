"""Online appendix of manuscript draft v2.20: the material that v2.19 had in Appendices A to C and that v2.20 keeps only in the
repository (prompt template, Tables S1-S6, definitions of the analyses of Section V-M). Built from the v2.19 LaTeX source, so every
number is the one that v2.19 printed.
    python make_online_appendix_v220.py
"""
import re
import subprocess
from pathlib import Path

B = Path("/home/claude/v215")
SRC = (B / "texp" / "EdgeSAR_IEEE_Access_v219.tex").read_text(encoding="utf-8")
OUT = B / "online_appendix"
OUT.mkdir(exist_ok=True)


def table_block(label, new_label):
    i = SRC.index("\\label{%s}" % label)
    a = SRC.rindex("\\begin{table*}", 0, i)
    b = SRC.index("\\end{table*}", i) + len("\\end{table*}")
    t = SRC[a:b].replace("\\begin{table*}[!tp]", "\\begin{table}[!htbp]").replace("\\end{table*}", "\\end{table}")
    return t.replace("\\label{%s}" % label, "\\label{%s}" % new_label)


def para(prefix):
    hits = [l for l in SRC.split("\n") if l.startswith(prefix)]
    assert len(hits) == 1, prefix
    return hits[0]


# prompt template (v2.19 Appendix A), without its section heading
a = SRC.index("\\section*{Appendix A: Prompt Template}") + len("\\section*{Appendix A: Prompt Template}")
b = SRC.index("\\section*{Appendix B: Additional Tables}")
prompt = SRC[a:b].replace(" \\textit{Text drafted with Claude \\cite{bAI}; see Acknowledgment.}", "")

# definitions (v2.19 Appendix C) and the recalibration equation (v2.19 Section V-J.8)
defs = [para("\\textbf{Label-using adaptations (Table C1).}"), para("\\textbf{Unlabeled budget (Table C2).}"),
        para("\\textbf{Field substitution (Table C3).}"), para("\\textbf{Robustness (Table C4).}")]
recal = SRC[SRC.index("\\textbf{8. A decision-level recalibration comparator.}"):]
recal = recal[:recal.index("Both start from offsets of 0 and scales of 1 and are fitted with SciPy's L-BFGS-B routine")]
recal = recal + ("Both start from offsets of 0 and scales of 1 and are fitted with SciPy's L-BFGS-B routine (the bound-constrained variant of "
                 "L-BFGS), with no bounds set; the penalty weight was set once, without tuning.")
recal = recal.replace("\\textbf{8. A decision-level recalibration comparator.}", "\\textbf{Recalibration comparators (Section V-J.5 of the paper).}")
recal = recal.replace("\\label{eq:7}", "\\label{eq:S1}").replace("the \\(w_{h,k}\\) of (2)", "the \\(w_{h,k}\\) of (2) of the paper")

body = "\n\n".join(defs)
MAP = (("Table C1", "Table S5"), ("Table C2", "Table A1 of the paper"), ("Table C3", "Table S6"), ("Table C4", "Table A2 of the paper"),
       ("Section V-J.8", "Section V-J.5"), ("as in (7) with", "as in (S1) with"), ("Section V-F", "Section V-F of the paper"),
       ("those of Table 4", "those of Table 4 of the paper"), ("Section IV-A", "Section IV-A of the paper"),
       ("the map of Table 4", "the map of Table 4 of the paper"), ("Section V-M.10", "Section V-M.3 of the paper"))
for o, n in MAP:
    body = body.replace(o, n)
body = body.replace(" \\textit{Text drafted with Claude \\cite{bAI}; see Acknowledgment.}", "")
body = body.replace("\\cite{b57}", "[57]").replace("\\cite{b58}", "[58]")
recal = recal.replace("\\cite{b55}", "[56]")

tabs1 = [table_block("tab9", "tabS1"), table_block("tab12", "tabS2"), table_block("tab10", "tabS3"), table_block("tab11", "tabS4")]
tabs2 = [table_block("tabC1", "tabS5"), table_block("tabC3", "tabS6")]
tabs = "\n\n".join(tabs1 + tabs2)
for o, n in (("Table 5", "Table 5 of the paper"), ("Table 4", "Table 4 of the paper"), ("(Section V-M.10;", "(Section V-M.3 of the paper;")):
    tabs = tabs.replace(o, n)

doc = r"""\documentclass[10pt]{article}
\usepackage[letterpaper,margin=0.75in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{amsmath,amssymb}
\usepackage{array}
\usepackage{url}
\usepackage{needspace}
\usepackage{float}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\theequation}{S\arabic{equation}}
\setlength{\parskip}{4pt}
\begin{document}
\begin{center}
{\large\bfseries Online appendix}\\[4pt]
Adapting a Hidden-State Task Classifier to a 4-Bit Language Model: Missed Incidents and a Label-Free Check in Simulated Multi-UAV Rescue\\[2pt]
S.\,V. Dissanayake, A. Aponso, M. Edirisooriya --- manuscript draft v2.20 (repository tag paper-v2.20)
\end{center}

This appendix holds the material that the manuscript cites as Tables S1 to S6, the prompt template and the definitions of the further
exploratory checks of Section V-M. Section, table, equation and reference numbers without the prefix S refer to the manuscript. Every
analysis here is exploratory (not pre-specified). The result files behind each table are listed in \texttt{PAPER\_MANIFEST\_v2.20.md}.
Text drafted with Claude (Anthropic); see the Acknowledgment of the manuscript.

\section*{S-A. Prompt template}
""" + prompt + r"""

\section*{S-B. Exploratory analyses of the first confirmation (Section V-J)}

Tables S1 to S4 give details of Section V-J.

\section*{S-C. Further exploratory checks (Section V-M)}

""" + body + "\n\n" + recal + r"""

Tables S5 and S6 give details of Sections V-M.1 and V-M.4; Tables A1 and A2 of the manuscript those of Sections V-M.3, V-M.5 and V-M.7.

\clearpage
""" + tabs + r"""

\end{document}
"""
assert "\\cite{" not in doc.replace("\\cite{b", "@@"), "unresolved citation"
left = re.findall(r"\\cite\{[^}]*\}", doc)
assert not left, left
(OUT / "ONLINE_APPENDIX_v2.20.tex").write_text(doc, encoding="utf-8")
for k in range(2):
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "ONLINE_APPENDIX_v2.20.tex"], cwd=OUT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
log = (OUT / "ONLINE_APPENDIX_v2.20.log").read_text(errors="replace")
print([l for l in subprocess.run(["pdfinfo", str(OUT / "ONLINE_APPENDIX_v2.20.pdf")], capture_output=True, text=True).stdout.splitlines() if l.startswith("Pages")])
for l in log.splitlines():
    if l.startswith("!") or "undefined" in l or ("Overfull" in l and "too wide" in l):
        print("LOG:", l)
