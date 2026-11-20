# EdgeSAR-Reports-1400

1,400 synthetic UAV flood-rescue field reports with gold task records, plus the code of the EdgeSAR study (4-bit quantisation of Llama 3.2 1B Instruct for a multi-UAV task allocator).

* **Data:** `data/cases.jsonl` (CC BY 4.0). Fields and limits: `DATA_CARD.md`.
* **Check it:** `python verify_dataset.py` (standard library only). It regenerates the set from `generator/` and compares the hash.
* **Code:** `code/` keeps the original folder layout (`edgesar_pilot`, `edgesar_heads`, `edgesar_shield`, `V1`), MIT licence. Start with `code/edgesar_shield/README.md`. Needs Python 3.12+, numpy, scipy, scikit-learn, pytest.
* **Not included:** model weights and hidden vectors (Llama 3.2 licence). See `DATA_CARD.md`, section 9.
* **Cite:** `CITATION.cff`.

Status of the study: the main result is a measurement and a set of controls, with negative results kept visible (`code/edgesar_shield/results/iter2/ITER2_SUMMARY.md`). It is not a new algorithm.
