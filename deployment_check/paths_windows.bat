@echo off
rem ---------------------------------------------------------------------------------------------------
rem Folders used by all steps. Change a line ONLY if that folder is somewhere else on your computer.
rem (This file lives in ...\edgesar_shield\submission\DEPLOYMENT_CHECK, so the workspace is 3 levels up.)
rem ---------------------------------------------------------------------------------------------------
for %%I in ("%~dp0..\..\..") do set "WORKSPACE=%%~fI"
set "REPAIR="
for %%D in ("%WORKSPACE%\edgesar_shield\repair_pkg\edgesar_repair_2026-11-14" "%WORKSPACE%\edgesar_shield\repair_package" "%WORKSPACE%\edgesar_repair_2026-11-14" "%WORKSPACE%\repair_pkg\edgesar_repair_2026-11-14" "%WORKSPACE%\repair_package") do if not defined REPAIR if exist "%%~D\ppr_lib.py" set "REPAIR=%%~D"
if not defined REPAIR set "REPAIR=%WORKSPACE%\edgesar_shield\repair_pkg\edgesar_repair_2026-11-14"
rem REPAIR = the folder that holds ppr_lib.py and out2\predictions.csv (the saved predictions). The program also searches for it by itself.
set "LLAMA_SRC=%WORKSPACE%\llama\llama-b11901-bin-win-cuda-12.4-x64"
if not exist "%LLAMA_SRC%\llama-server.exe" set "LLAMA_SRC=D:\llama"
if not exist "%LLAMA_SRC%\llama-server.exe" for /d %%D in ("D:\llama\llama-b11901*") do if exist "%%~D\llama-server.exe" set "LLAMA_SRC=%%~D"
set "LLAMA_CPU=D:\llama_cpu_edgesar_v1_1"
set "MODEL=D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf"
set "SERVER=%LLAMA_CPU%\llama-server.exe"
