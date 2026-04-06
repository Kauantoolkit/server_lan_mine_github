@echo off
echo ============================================
echo  Build — Minecraft Server Sync
echo ============================================
echo.

echo [1/3] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller --quiet
)

echo [2/3] Gerando sync.exe...
pyinstaller --onefile --console --name sync sync.py
if errorlevel 1 (
    echo.
    echo ERRO ao gerar sync.exe
    pause
    exit /b 1
)

echo [3/3] Gerando server_setup.exe...
pyinstaller --onefile --console --name server_setup server_setup.py
if errorlevel 1 (
    echo.
    echo ERRO ao gerar server_setup.exe
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Pronto! Executaveis gerados em: dist\
echo    dist\sync.exe
echo    dist\server_setup.exe
echo ============================================
echo.
echo Copie os .exe para a pasta do repositorio
echo junto com config.json e execute normalmente.
echo.
pause
