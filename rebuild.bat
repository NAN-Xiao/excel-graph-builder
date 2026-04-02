@echo off
chcp 65001 >nul
title Excel Graph Builder - 清理并重新构建

:: 确保工作目录是脚本所在目录
cd /d "%~dp0"

set "SCRIPT_DIR=%~dp0"
set "CONFIG_FILE=%SCRIPT_DIR%configs\settings.yml"

echo ==========================================
echo   清理并重新构建
echo ==========================================
echo.

:: ── 读取配置获取 graph_dir 和 task_name ──
set "TASK_NAME=ExcelGraphBuilder"
set "GRAPH_DIR=..\graph"

if exist "%CONFIG_FILE%" (
    setlocal enabledelayedexpansion
    for /f "usebackq delims=" %%a in ("%CONFIG_FILE%") do (
        set "line=%%a"
        if not "!line!"=="" (
            set "first_char=!line:~0,1!"
            if not "!first_char!"=="#" (
                for /f "tokens=1,* delims=:" %%b in ("!line!") do (
                    set "_key=%%b"
                    set "_val=%%c"
                    for /f "tokens=*" %%k in ("!_key!") do set "_key=%%k"
                    if defined _val for /f "tokens=*" %%v in ("!_val!") do set "_val=%%v"
                    if "!_key!"=="task_name" set "_TN=!_val!"
                    if "!_key!"=="graph_dir" set "_GD=!_val!"
                )
            )
        )
    )
    endlocal & (
        if defined _TN set "TASK_NAME=%_TN%"
        if defined _GD set "GRAPH_DIR=%_GD%"
    )
)

for %%i in ("%SCRIPT_DIR%%GRAPH_DIR%") do set "GRAPH_DIR_ABS=%%~fi"

echo   配置: %CONFIG_FILE%
echo   产出: %GRAPH_DIR_ABS%
echo.

:: ── Step 1: 清理旧构建产物 ──
echo [1/3] 清理旧构建产物...
if exist "%GRAPH_DIR_ABS%\current" (
    rmdir /s /q "%GRAPH_DIR_ABS%\current"
    echo   已清理 current\
)
if exist "%GRAPH_DIR_ABS%\latest_success" (
    rmdir /s /q "%GRAPH_DIR_ABS%\latest_success"
    echo   已清理 latest_success\
)
if exist "%GRAPH_DIR_ABS%\builds" (
    rmdir /s /q "%GRAPH_DIR_ABS%\builds"
    echo   已清理 builds\
)
if exist "%GRAPH_DIR_ABS%\reports" (
    rmdir /s /q "%GRAPH_DIR_ABS%\reports"
    echo   已清理 reports\
)
if exist "%GRAPH_DIR_ABS%\schema_graph.json" (
    del /q "%GRAPH_DIR_ABS%\schema_graph.json"
    echo   已清理 schema_graph.json
)
if exist "%GRAPH_DIR_ABS%\alerts.log" (
    del /q "%GRAPH_DIR_ABS%\alerts.log"
    echo   已清理 alerts.log
)
echo   清理完成
echo.

:: ── Step 2: 检测执行方式（exe 或 python） ──
echo [2/3] 执行全量构建...
echo.

set "EXE_PATH=%SCRIPT_DIR%..\dist\indexer.exe"
set "DIST_CONFIG=%SCRIPT_DIR%..\dist\configs\settings.yml"

if exist "%EXE_PATH%" (
    echo   使用: %EXE_PATH%
    "%EXE_PATH%" --config "%DIST_CONFIG%" --run-now
) else (
    echo   使用: python -m indexer
    set "VENV_DIR=%SCRIPT_DIR%.venv"
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        call "%VENV_DIR%\Scripts\activate.bat"
    )
    python -m indexer --config "%CONFIG_FILE%" --run-now
)

if errorlevel 1 (
    echo.
    echo [错误] 构建失败！
    pause
    exit /b 1
)

:: ── Step 3: 验证结果 ──
echo.
echo [3/3] 验证构建结果...

if exist "%GRAPH_DIR_ABS%\current\schema_summary.txt" (
    echo   [OK] current\ 已更新
) else (
    echo   [警告] current\ 未生成，请检查 reports\ 和 alerts.log
)

echo.
echo ==========================================
echo   重新构建完成！
echo ==========================================
echo.
pause
