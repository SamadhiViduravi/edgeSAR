@echo off
cd /d "%~dp0"
echo Check confirmation, GPU step: vectors of 5,000 new reports (FP16, Q4_K_M, Q3_K_M) and 1,400 development reports (Q3_K_M).
echo About 40 minutes with the GPU. Keep the charger plugged in. Do not use the computer for heavy work. Do not close this window.
echo If it stops, run this file again: it continues where it stopped.
echo.
python extract_c.py
echo.
echo If you see "ALL DONE", tell Claude: extraction finished.
echo If you see STOP or an error, copy all the text in this window and send it to Claude.
pause
