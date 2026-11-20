# Reproducibility

Run `pytest` from the root. The null rerun test completes the same scenario three times (including reset) and compares exact state/event dictionaries. Movement tests check every executed segment against inflated obstacles. Tests also cover service duration, task ordering, invalid fixtures, WebSocket handshake, API commands and pause stability.

The seed, scenario version, SHA-256 and tick configuration are included in audit exports. Python dependencies are frozen in requirements.lock; npm dependencies are frozen in package-lock.json. Regenerate the schema using `python -m scripts.generate_schema` from the root. `scripts/create_scenario.py` authors the committed default fixture; runtime never regenerates it.

Determinism applies to identical simulation inputs and command sequences, not operating-system wall-clock timing or cross-platform floating-point bit equivalence. Snapshot restore/fork, event replay, commit capture and model provenance are deferred. The export is sufficient to inspect current inputs and outcomes, not an advertised experiment record for a quantization study.
