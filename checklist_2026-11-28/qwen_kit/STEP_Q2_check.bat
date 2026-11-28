@echo off
cd /d "%~dp0"
echo STEP Q2: quick check, about 3-5 minutes. Do not close this window.
echo It starts each Qwen model, checks the prompt format, and embeds 20 old reports twice.
echo.
python qwen_extract.py --check
echo.
echo If you see "CHECK PASSED for both models", copy this window text to Claude and run STEP_Q3_extract.bat.
echo If you see STOP or an error, copy all the text in this window and send it to Claude.
pause
