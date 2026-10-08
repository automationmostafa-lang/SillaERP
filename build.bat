@echo off
title HyperMarket Build
echo ============================================
echo Building HyperMarket.exe ...
pyinstaller --onefile --windowed --name "HyperMarket" --icon=logo.ico --add-data "logo.png;." --collect-all qrcode --noconfirm --clean main.py
echo Copying assets ...
copy /Y logo.ico dist\logo.ico >nul 2>&1
copy /Y logo.png dist\logo.png >nul 2>&1
copy /Y create_shortcut.py dist\create_shortcut.py >nul 2>&1
echo DONE - files: dist\HyperMarket.exe
pause