@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo PyInstaller not found. Installing requirements...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\pyinstaller.exe" --noconfirm --windowed --name DrugCards main.py

