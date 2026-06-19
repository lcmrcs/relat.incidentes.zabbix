@echo off
setlocal

cd /d "%~dp0"

echo ===============================================
echo Relatorio Zabbix - Terminais Faciais
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

if not exist "zabbix-report\.env" (
    echo ERRO: arquivo zabbix-report\.env nao encontrado.
    echo.
    echo Crie esse arquivo a partir de zabbix-report\.env.example
    echo e preencha ZABBIX_URL e ZABBIX_TOKEN.
    echo.
    pause
    exit /b 1
)

if not exist "zabbix-report\venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Criando venv...
    %PYTHON_CMD% -m venv "zabbix-report\venv"
    if errorlevel 1 (
        echo.
        echo ERRO: nao foi possivel criar a venv.
        echo Verifique se o Python esta instalado e marcado no PATH.
        pause
        exit /b 1
    )
)

call "zabbix-report\venv\Scripts\activate.bat"

echo Instalando ou atualizando dependencias...
python -m pip install -r "zabbix-report\requirements.txt"
if errorlevel 1 (
    echo.
    echo ERRO: falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo Gerando relatorio exclusivo de Terminal Facial...
python "zabbix-report\zabbix_report.py" --periodo historico --status abertos --equipamento "Terminal Facial"
if errorlevel 1 (
    echo.
    echo ERRO: falha ao gerar o relatorio.
    pause
    exit /b 1
)

set "LAST_HTML="
for /f "delims=" %%F in ('dir /b /o-d "zabbix-report\reports\*terminal_facial.html" 2^>nul') do (
    set "LAST_HTML=%%F"
    goto :open_report
)

:open_report
if defined LAST_HTML (
    echo.
    echo Abrindo relatorio: %LAST_HTML%
    start "" "%CD%\zabbix-report\reports\%LAST_HTML%"
) else (
    echo.
    echo Relatorio gerado, mas nenhum HTML de Terminal Facial foi encontrado.
    echo Verifique a pasta zabbix-report\reports.
)

echo.
echo Finalizado.
pause
