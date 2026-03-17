@echo off
chcp 65001 >nul
title Config Indexer

:: 当前目录即 Excel 数据所在目录
set "SCRIPT_DIR=%~dp0"
set "DATA_ROOT=%SCRIPT_DIR%"
set "GRAPH_DIR=%SCRIPT_DIR%graph"

:: 创建输出目录
if not exist "%GRAPH_DIR%" mkdir "%GRAPH_DIR%"

echo ==========================================
echo   Config Indexer
echo ==========================================
echo.
echo   数据目录: %DATA_ROOT%
echo   输出目录: %GRAPH_DIR%
echo.

:: 执行增量构建
"%SCRIPT_DIR%indexer.exe" ^
    --data-root "%DATA_ROOT%" ^
    --storage-dir "%GRAPH_DIR%" ^
    --html-dir "%GRAPH_DIR%" ^
    --run-now

echo.
pause
