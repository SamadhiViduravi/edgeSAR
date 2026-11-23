@echo off
cd /d "%~dp0"
call paths_windows.bat
echo OPTIONAL. Re-creates the folded classifier from your saved vectors (this step uses the FP16 vectors; the benchmark does not).
echo It compares the new files with the files that came with this folder.
python export_folded_classifier.py --root "%WORKSPACE%" --repair-dir "%REPAIR%" --out "out\folded_recreated" --compare-with "folded"
echo.
echo Expected: "400 of 400" in both rows of the table, and "SAME as the shipped files".
pause
