@echo off
cd /d "%~dp0"
call paths_windows.bat
echo RUN A (main run): CPU only, same settings as the saved vectors, all 400 style-B reports. This is the longest run.
echo The program prints how much time is left. Do not use the computer for other work while it runs.
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\A_cpu_mmap_ctx4096_400reports" --label "A: CPU only, as extracted (mmap, ctx 4096), 400 reports" --episodes 20
echo.
echo Finished or stopped. Open out\A_cpu_mmap_ctx4096_400reports\DEPLOYMENT_REPORT.md in Notepad.
pause
