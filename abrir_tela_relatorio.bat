@echo off
setlocal

cd /d "%~dp0"

echo ===============================================
echo Central de Relatorios Zabbix
echo ===============================================
echo.

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo ERRO: Python nao encontrado.
        echo.
        echo Instale o Python e marque a opcao "Add Python to PATH".
        echo Depois execute este arquivo novamente.
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

if not exist "zabbix-report\venv-windows\Scripts\python.exe" (
    echo Ambiente virtual do Windows nao encontrado. Criando venv...
    %PYTHON_CMD% -m venv "zabbix-report\venv-windows"
    if errorlevel 1 (
        echo.
        echo ERRO: nao foi possivel criar a venv.
        pause
        exit /b 1
    )
)

call "zabbix-report\venv-windows\Scripts\activate.bat"

echo Instalando ou atualizando dependencias...
python -m pip install -r "zabbix-report\requirements.txt"
if errorlevel 1 (
    echo.
    echo ERRO: falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo Abrindo tela local no navegador...
python "zabbix-report\report_launcher.py"

echo.
echo Tela encerrada.
pause
