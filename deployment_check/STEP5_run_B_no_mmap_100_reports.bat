@echo off
cd /d "%~dp0"
call paths_windows.bat
echo RUN B: weights loaded into private memory (no memory mapping), 100 reports.
echo The program prints how much time is left. Do not use the computer for other work while it runs.
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\B_cpu_nommap_ctx4096_100reports" --label "B: CPU only, weights in private memory (no-mmap), ctx 4096, 100 reports" --no-mmap --episodes 5
echo.
echo Finished or stopped. Open out\B_cpu_nommap_ctx4096_100reports\DEPLOYMENT_REPORT.md in Notepad.
pause
