@echo off
cd /d "%~dp0"
call paths_windows.bat
echo RUN D: like C, but Windows is told that all processes together may commit at most 2048 MB. If the program cannot start or crashes, that is also a result.
echo The program prints how much time is left. Do not use the computer for other work while it runs.
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\D_cap2048_nommap_ctx1024_100reports" --label "D: as C, with a 2048 MB hard cap on committed memory of all processes" --no-mmap --ctx 1024 --episodes 5 --job-limit-mb 2048
echo.
echo Finished or stopped. Open out\D_cap2048_nommap_ctx1024_100reports\DEPLOYMENT_REPORT.md in Notepad.
pause
