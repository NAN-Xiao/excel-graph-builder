@echo off
chcp 65001 >nul
title Excel Graph Builder - 安装定时任务

:: ============================================================
::   Excel Graph Builder — 安装定时任务
::
::   执行内容：
::     1. 立即执行一次增量构建（确认环境正常）
::     2. 注册 Windows 计划任务，每天定时自动构建
::
::   默认时间: 每天 02:00
::   如需修改，编辑下方 SCHEDULE_TIME 变量
::
::   注意: 注册计划任务需要管理员权限
::         右键此文件 → 以管理员身份运行
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%indexer.exe"
set "DATA_ROOT=%SCRIPT_DIR%"
set "GRAPH_DIR=%SCRIPT_DIR%graph"
set "TASK_NAME=ExcelGraphBuilder"
set "SCHEDULE_TIME=02:00"

:: 检查 exe
if not exist "%EXE_PATH%" (
    echo [错误] 未找到 indexer.exe
    echo   请确认 install.bat 与 indexer.exe 在同一目录
    pause
    exit /b 1
)

:: 创建输出目录
if not exist "%GRAPH_DIR%" mkdir "%GRAPH_DIR%"

echo ==========================================
echo   Excel Graph Builder - 安装
echo ==========================================
echo.
echo   数据目录: %DATA_ROOT%
echo   输出目录: %GRAPH_DIR%
echo.

:: ── Step 1: 立即执行首次构建 ──
echo [1/2] 执行首次构建...
echo.

"%EXE_PATH%" ^
    --data-root "%DATA_ROOT%" ^
    --storage-dir "%GRAPH_DIR%" ^
    --html-dir "%GRAPH_DIR%" ^
    --run-now

if errorlevel 1 (
    echo.
    echo [警告] 首次构建可能未完全成功，但将继续注册定时任务
    echo.
)

:: ── Step 2: 注册 Windows 计划任务 ──
echo.
echo [2/2] 注册 Windows 计划任务...
echo   任务名称: %TASK_NAME%
echo   执行时间: 每天 %SCHEDULE_TIME%
echo.

:: 删除已有同名任务
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

:: 创建计划任务
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "\"%EXE_PATH%\" --data-root \"%DATA_ROOT%\" --storage-dir \"%GRAPH_DIR%\" --html-dir \"%GRAPH_DIR%\" --run-now" ^
    /SC DAILY ^
    /ST %SCHEDULE_TIME% ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo.
    echo [错误] 计划任务注册失败！
    echo   请以管理员身份运行此脚本（右键 → 以管理员身份运行）
    echo.
    echo   首次构建已完成，手动执行请双击 indexer.exe
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo   首次构建: 已完成
echo   定时任务: 每天 %SCHEDULE_TIME% 自动执行
echo.
echo   输出目录: %GRAPH_DIR%\
echo   手动触发: schtasks /Run /TN "%TASK_NAME%"
echo   卸载任务: 运行 uninstall.bat
echo.
echo ==========================================
pause
