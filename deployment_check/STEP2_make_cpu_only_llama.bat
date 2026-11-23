@echo off
cd /d "%~dp0"
call paths_windows.bat
python prepare_cpu_runtime.py --source "%LLAMA_SRC%" --destination "%LLAMA_CPU%"
if errorlevel 1 (
  echo CPU setup FAILED. Copy the output for review; do not continue.
  pause
  exit /b 1
)
echo CPU runtime ready in %LLAMA_CPU%.
pause
