CHECK CONFIRMATION (26 Nov 2026) - what to do

1. FIRST make the plan public (before running anything):
   the same files are in your GitHub repo folder: check_confirmation\
   Push them with the tag check-protocol-2026-11-26 (commands are in Claude's message).

2. THEN double-click RUN_EXTRACT_C.bat in this folder.
   It checks the GPU vectors (anchor check), makes Q3_K_M if it is missing, and makes the vectors.
   About 40 minutes. If it stops, run it again: it continues.

3. When you see "ALL DONE", tell Claude: extraction finished.
   Claude copies the folder vectors_C\ directly from your laptop. You do not need to upload anything.

Do not change any file in this folder. Their SHA-256 values are in FROZEN.sha256.
