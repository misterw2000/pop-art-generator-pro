@echo off
cd /d "C:\Users\A\Desktop\PROJECTS\pop_art_generator_pro"

echo Creating __init__.py files...
python -c "import os; [open(os.path.join(d, '__init__.py'), 'a').close() for d in ['services', 'ui', 'core', 'core/models', 'infrastructure', 'infrastructure/gpu']]"

echo Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist main.spec del main.spec

echo Building EXE (This may take a few minutes)...
.\venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --icon=logo.ico --add-data "logo.ico;." --collect-all customtkinter --collect-all numpy --collect-all tkinterdnd2 --hidden-import cv2 --hidden-import PIL --paths "C:\Users\A\Desktop\PROJECTS\pop_art_generator_pro" main.py

echo Done! Check the dist folder.
pause