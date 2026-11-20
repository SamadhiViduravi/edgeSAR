# M4 report: heads, candidates, conformal sets (development set, saved vectors)

Style A only; 5 outer folds (EVAL 200, CAL 200, FIT about 515 after removing exact duplicates of CAL/EVAL reports). Heads: standardise + logistic regression, C by grouped CV inside FIT, tol 1e-6.

Head fits: {"fits": 45, "hit_iteration_limit": 0, "chosen_C": {"0.003": 22, "0.03": 8, "3": 15}, "seconds": 153.5, "tol": 1e-06, "max_iter": 3000}

## Readout accuracy on EVAL (pooled over the 5 folds, n = 1000)

| Arm | action correct | whole record correct | gold record expressible by heads+parser |
|---|---|---|---|
| q4 | 98.3% | 74.3% | 100.0% |
| f16 | 99.3% | 79.3% | 100.0% |
| q8 | 99.2% | 78.0% | 100.0% |
| rec | 95.6% | 71.3% | 100.0% |
| raw | 73.5% | 53.5% | 100.0% |

## Enumeration (Q4 heads)

At most 20 combinations per report (the plan's 22 counts CREATE and UPDATE twice). Distinct merged candidates per report: {1: 200, 10: 900, 20: 900}.
Reports (CAL and EVAL roles together, 2000 rows) whose gold record the heads + parser cannot express: 0 unique reports.

By gold action: {}.

## Two kinds of top record (Q4, EVAL)

The hierarchical record (pilot rule, what A1 commits) and the single most probable candidate differ in 4 of 1000 reports (0.4%). Of those: hierarchical right and top wrong 0; hierarchical wrong and top right 1; both wrong 3.

## Conformal sets (Q4 heads; threshold from CAL of each fold; numbers on EVAL, pooled n = 1000)

| alpha | target | coverage | 95% band (binomial, n=1000) | inside? | empty | size 1 | size 2-8 | size > 8 | top in set | hier in set | mean size |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | 95% | 94.9% | 93.6%-96.4% | yes | 0 | 529 | 469 | 2 | 100.0% | 100.0% | 2.16 |
| 0.10 | 90% | 90.8% | 88.1%-91.9% | yes | 1 | 568 | 431 | 0 | 99.9% | 99.9% | 1.69 |
| 0.20 | 80% | 80.7% | 77.5%-82.5% | yes | 27 | 768 | 205 | 0 | 97.3% | 97.1% | 1.19 |

Per fold (coverage on the 200 EVAL reports of each fold; the threshold comes from the 200 CAL reports of that fold):

* alpha 0.05: fold 0 q=0.947 cal 0.955 eval 0.945; fold 1 q=0.918 cal 0.955 eval 0.930; fold 2 q=0.910 cal 0.955 eval 0.955; fold 3 q=0.918 cal 0.955 eval 0.955; fold 4 q=0.932 cal 0.955 eval 0.960
* alpha 0.10: fold 0 q=0.904 cal 0.905 eval 0.930; fold 1 q=0.842 cal 0.905 eval 0.870; fold 2 q=0.862 cal 0.905 eval 0.905; fold 3 q=0.858 cal 0.905 eval 0.925; fold 4 q=0.876 cal 0.905 eval 0.910
* alpha 0.20: fold 0 q=0.794 cal 0.805 eval 0.815; fold 1 q=0.743 cal 0.805 eval 0.785; fold 2 q=0.748 cal 0.805 eval 0.790; fold 3 q=0.746 cal 0.805 eval 0.835; fold 4 q=0.730 cal 0.805 eval 0.810

Reading: the band above is the sampling error of the 1000 EVAL reports only. The threshold itself is estimated from 200 reports per fold, so the true spread is a little wider (about sqrt(2) times).  Coverage is marginal and holds under exchangeability of CAL and EVAL reports; the reports of one family are NOT independent, so the guarantee is approximate here (plan 4.8).
