@echo off
echo ============================================
echo   Building Unnamedtech Support Tool
echo ============================================
echo.

pip install -r requirements.txt

echo.
echo Building .exe ...
echo.

python -m PyInstaller --onefile --noconsole --name "Unnamedtech Support Tool" --uac-admin --icon="Unnamed_multi.ico" --add-data="Unnamed_multi.ico;." --collect-all customtkinter support_tool.py

echo.
echo ============================================
echo   Build complete!
echo   EXE is in: dist\Unnamedtech Support Tool.exe
echo ============================================
pause
