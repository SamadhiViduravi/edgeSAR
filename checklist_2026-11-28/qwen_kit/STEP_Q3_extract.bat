@echo off
cd /d "%~dp0"
echo STEP Q3: make the Qwen vectors of the 1,400 development and 7,000 fresh reports. About 1.5 to 3 hours with the GPU.
echo Keep the charger plugged in. Do not let the laptop sleep. Do not close this window.
echo If it stops, run this file again: it continues where it stopped.
echo.
python qwen_extract.py
echo.
echo If you see "ALL DONE", tell Claude: Qwen extraction finished.
echo If you see STOP or an error, copy all the text in this window and send it to Claude.
pause
