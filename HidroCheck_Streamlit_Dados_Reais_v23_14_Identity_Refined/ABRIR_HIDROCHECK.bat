@echo off
setlocal EnableExtensions EnableDelayedExpansion

title HidroCheck - Execucao Local

echo.
echo ==========================================
echo   HidroCheck - Operacao do Sistema
echo          de Monitoramento
echo ==========================================
echo.

REM Verifica se o launcher "py" existe
where py >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Python launcher "py" nao foi encontrado neste computador.
    echo.
    echo Se o Python estiver instalado, tente abrir o PowerShell e executar:
    echo   py --version
    echo.
    pause
    exit /b 1
)

REM Procura streamlit_app.py na pasta do BAT
set "APP="

if exist "%~dp0streamlit_app.py" (
    set "APP=%~dp0streamlit_app.py"
)

REM Procura em subpastas imediatas
if not defined APP (
    for /d %%D in ("%~dp0*") do (
        if exist "%%~fD\streamlit_app.py" (
            set "APP=%%~fD\streamlit_app.py"
            goto :found
        )
    )
)

REM Procura recursivamente como ultimo recurso
if not defined APP (
    for /r "%~dp0" %%F in (streamlit_app.py) do (
        set "APP=%%~fF"
        goto :found
    )
)

:found
if not defined APP (
    echo [ERRO] Nao encontrei o arquivo streamlit_app.py.
    echo.
    echo Coloque este .bat dentro da pasta extraida do HidroCheck v23
    echo ou em uma pasta acima dela.
    echo.
    pause
    exit /b 1
)

for %%F in ("%APP%") do set "APPDIR=%%~dpF"

echo Aplicacao encontrada:
echo   %APP%
echo.

REM Verifica se Streamlit esta instalado
py -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Streamlit nao encontrado. Tentando instalar dependencias...
    echo.

    if exist "%APPDIR%requirements.txt" (
        py -m pip install -r "%APPDIR%requirements.txt"
    ) else (
        py -m pip install streamlit pandas numpy plotly openpyxl Pillow
    )

    if errorlevel 1 (
        echo.
        echo [ERRO] Nao foi possivel instalar as dependencias.
        echo Pode haver bloqueio de TI/rede corporativa.
        echo.
        pause
        exit /b 1
    )
)

REM Encerra apenas tentativa anterior nesta porta, se houver, nao e obrigatorio
echo Iniciando HidroCheck apenas neste computador...
echo Endereco local: http://127.0.0.1:8501
echo.
echo IMPORTANTE:
echo - Esta execucao e LOCAL.
echo - Nao usa o Streamlit Cloud.
echo - Mantenha esta janela aberta enquanto estiver usando o HidroCheck.
echo - Para encerrar, pressione Ctrl+C.
echo.

REM Abre o navegador depois de pequeno atraso
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8501"

cd /d "%APPDIR%"
py -m streamlit run "%APP%" --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false

echo.
echo HidroCheck encerrado.
pause
