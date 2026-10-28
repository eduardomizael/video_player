@echo off
chcp 65001 > nul
pushd "%~dp0"
echo =========================================
echo  Compilador do Editor - Webview
echo =========================================
echo.
uv run --extra webview --group dev python build.py --webview
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel gerar a versao webview.
    popd
    pause
    exit /b 1
)
echo.
popd
pause
