@echo off
cd /d "%~dp0"
echo STEP Q1: download the Qwen2.5-1.5B FP16 file (3.56 GB), check it, and make the Q4_K_M file.
echo If the internet stops, run this file again: it continues where it stopped.
echo.
python qwen_download.py
echo.
echo If you see "DONE", run STEP_Q2_check.bat.
echo If you see STOP or an error, copy all the text in this window and send it to Claude.
pause
