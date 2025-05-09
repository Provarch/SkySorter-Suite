@echo off
title SkySorterPro Setup and Run

echo Checking for Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Downloading and installing Python...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    echo Installing Python silently...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    echo Python installation complete.
) else (
    echo Python is already installed.
)

echo Ensuring pip is installed...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo Creating requirements.txt...
echo discord.py > requirements.txt
echo imagehash >> requirements.txt
echo piexif >> requirements.txt
echo Pillow >> requirements.txt
echo PyQt6 >> requirements.txt
echo PyQt6-WebEngine >> requirements.txt
echo py7zr >> requirements.txt
echo pyexiv2 >> requirements.txt
echo requests >> requirements.txt
echo tkinterdnd2 >> requirements.txt

echo Installing required dependencies...
python -m pip install -r requirements.txt
del requirements.txt

echo Creating SkySorterPro desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$([Environment]::GetFolderPath('Desktop'))\SkySorterPro.lnk\"); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\UI.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\UI.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

echo Creating SkySorterPro local shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%CD%\SkySorterPro.lnk'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\UI.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\UI.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

echo Creating SkyDrop desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$([Environment]::GetFolderPath('Desktop'))\SkyDrop.lnk\"); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\__SkyDrop.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\skydrop.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

echo Creating SkyDrop local shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%CD%\SkyDrop.lnk'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\__SkyDrop.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\skydrop.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

echo Creating SkyNizer desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$([Environment]::GetFolderPath('Desktop'))\SkyNizer.lnk\"); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\__skyNizer.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\skyNizer.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

echo Creating SkyNizer local shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%CD%\SkyNizer.lnk'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%CD%\_internal\__skyNizer.pyw\"'; $Shortcut.IconLocation = '%CD%\_internal\_gfx\skyNizer.ico'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"