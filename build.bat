@echo off
chcp 65001 > nul
pushd "%~dp0"
echo =========================================
echo  Compilador do Editor de Capítulos
echo =========================================
echo.
uv run python build.py
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel gerar a versao classica.
    popd
    pause
    exit /b 1
)
echo.
popd
pause
