EdgeSAR - SECOND MODEL FAMILY (Mr. Maninda's checklist, item 5)
=================================================================
Model: Qwen2.5-1.5B-Instruct (Qwen team), FP16 and Q4_K_M, with the same llama.cpp build (D:\llama, b11901),
the same server settings, the same system prompt and user message, and the same reports as the Llama study.
Only Qwen's chat format is different. Nothing in the Llama study is changed.

This folder must stay next to edgesar_pilot and edgesar_fresh_2026-11-18 (it is: D:\1 Samadhi UNI\aFYP\Claude\).
Close any other llama-server window first. Keep the laptop plugged in. Do not let it sleep.

STEP Q1  Double-click STEP_Q1_download_and_quantize.bat
         Downloads 3.56 GB, checks it, and makes the Q4_K_M file (needs about 5 GB free on D:).
         If the internet stops, run it again: it continues.

STEP Q2  Double-click STEP_Q2_check.bat   (about 3-5 minutes)
         It must end with "CHECK PASSED for both models".
         Copy the whole window text and send it to Claude (it shows the time estimate).

STEP Q3  Double-click STEP_Q3_extract.bat (about 1.5 to 3 hours; you can use the laptop lightly meanwhile)
         Position "prefix" first (the main one), then "end".
         If it stops, double-click it again: it continues where it stopped.
         When it says ALL DONE, tell Claude: "Qwen extraction finished". Claude reads the files from this folder.

If anything prints STOP, copy the window text and send it to Claude.
