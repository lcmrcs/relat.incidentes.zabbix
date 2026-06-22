@echo off
setlocal

cd /d "%~dp0"

echo ===============================================
echo Relatorio Executivo de Incidentes Zabbix - Por Equipamento
echo ===============================================
echo.

set "EQUIPAMENTO=%~1"
if "%EQUIPAMENTO%"=="" (
    echo Digite o equipamento que deseja filtrar.
    echo.
    echo Exemplos:
    echo - Terminal Facial
    echo - Camera
    echo - Mikrotik
    echo - Switch
    echo - NVR
    echo - Central de Alarme
    echo - Portal Detector de Metal
    echo.
    set /p "EQUIPAMENTO=Equipamento: "
)

if "%EQUIPAMENTO%"=="" (
    echo ERRO: o equipamento nao pode ficar vazio.
    pause
    exit /b 1
)

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
    echo Arquivo zabbix-report\.env nao encontrado.
    echo.
    echo Vamos criar esse arquivo agora.
    echo Os dados ficarao salvos apenas neste computador.
    echo.
    set /p "ZABBIX_URL_INPUT=Digite a URL da API do Zabbix: "
    set /p "ZABBIX_TOKEN_INPUT=Digite o token da API do Zabbix: "
    echo.

    if "%ZABBIX_URL_INPUT%"=="" (
        echo ERRO: a URL do Zabbix nao pode ficar vazia.
        pause
        exit /b 1
    )

    if "%ZABBIX_TOKEN_INPUT%"=="" (
        echo ERRO: o token do Zabbix nao pode ficar vazio.
        pause
        exit /b 1
    )

    (
        echo ZABBIX_URL=%ZABBIX_URL_INPUT%
        echo ZABBIX_TOKEN=%ZABBIX_TOKEN_INPUT%
    ) > "zabbix-report\.env"

    echo Arquivo zabbix-report\.env criado com sucesso.
    echo.
)

if not exist "zabbix-report\venv-windows\Scripts\python.exe" (
    echo Ambiente virtual do Windows nao encontrado. Criando venv...
    %PYTHON_CMD% -m venv "zabbix-report\venv-windows"
    if errorlevel 1 (
        echo.
        echo ERRO: nao foi possivel criar a venv.
        echo Verifique se o Python esta instalado e marcado no PATH.
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
echo Gerando relatorio exclusivo de: %EQUIPAMENTO%
python "zabbix-report\zabbix_report.py" --periodo historico --status abertos --equipamento "%EQUIPAMENTO%"
if errorlevel 1 (
    echo.
    echo ERRO: falha ao gerar o relatorio.
    pause
    exit /b 1
)

set "LAST_HTML="
for /f "delims=" %%F in ('dir /b /o-d "zabbix-report\reports\*.html" 2^>nul') do (
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
    echo Relatorio gerado, mas nenhum HTML foi encontrado.
    echo Verifique a pasta zabbix-report\reports.
)

echo.
echo Finalizado.
pause
