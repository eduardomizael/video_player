@echo off
chcp 65001 > nul
echo =========================================
echo  Compilador do Editor de Capítulos
echo =========================================
echo.
uv run python build.py
echo.
pause
