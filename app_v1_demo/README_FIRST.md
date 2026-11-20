# Early web prototype (EdgeSAR Lab V1, October 2026): not used for the paper

This folder is the first software prototype of the EdgeSAR final-year project:

- a mission-control web app (Next.js + MapLibre frontend, FastAPI backend): a 2 km synthetic flood area, three simulated UAVs on predefined routes, Run / Pause / Step / Reset, layer toggles and audit export (version 0.1.0, 16 Oct 2026; see `CHANGELOG.md`);
- an allocation demo page (`/allocation`, end of October 2026) that shows five pilot cases through a simplified CBBA (`packages/allocation`).

It is kept as a record of the project's development. **None of the paper's results come from this folder.** The study code is in `zenodo_v1/`, `code/`, `development_study/` and `fresh_confirmation/`.

How to run: see `README.md` in this folder (Node.js 22+, Python 3.12+). `node_modules`, `.venv` and build folders are not included; `npm ci` and `pip install -r requirements.lock` recreate them.

Known limits:
- The map simulator page works on its own. The allocation page also needs the pilot model-output files (`edgesar_pilot/runs/*.jsonl`), which are not in this repository, and reads them from a fixed Windows path set in `packages/allocation/decisions.py` (`PILOT_DIR`).
- Routes and assignments in the map simulator are written in the scenario file; it has no language model and no CBBA (see `README.md`, "Architecture and responsibility boundaries").
