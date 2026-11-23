@echo off
cd /d "%~dp0"
call paths_windows.bat
echo RUN C: like B but context 1024 (the longest prompt has 670 tokens), 100 reports.
echo The program prints how much time is left. Do not use the computer for other work while it runs.
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\C_cpu_nommap_ctx1024_100reports" --label "C: CPU only, no-mmap, context 1024, 100 reports" --no-mmap --ctx 1024 --episodes 5
echo.
echo Finished or stopped. Open out\C_cpu_nommap_ctx1024_100reports\DEPLOYMENT_REPORT.md in Notepad.
pause
