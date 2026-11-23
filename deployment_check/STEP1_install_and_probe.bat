@echo off
cd /d "%~dp0"
call paths_windows.bat
echo Workspace folder: %WORKSPACE%
python --version
python -m pip install psutil numpy scipy scikit-learn
if errorlevel 1 exit /b 1
echo.
echo ---- 30 second check of the measurement tools ----
python deploy_bench.py probe --tmp "%TEMP%"
echo.
echo If the last line says "all parts that matter work", go to STEP2.
echo If it says "SOME PARTS FAILED", copy ALL the text above and send it to Claude. Do not run the other steps.
pause
