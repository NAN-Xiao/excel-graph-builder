@echo off
chcp 65001 >nul
title Config Indexer Service

echo ==========================================
echo   Config Indexer Service
echo ==========================================
echo.

:: 设置环境变量
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DATA_ROOT=%PROJECT_ROOT%\configs"
set "STORAGE_DIR=%PROJECT_ROOT%\data\indexer"
set "LOG_DIR=%PROJECT_ROOT%\logs"

:: 创建目录
if not exist "%STORAGE_DIR%" mkdir "%STORAGE_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 激活虚拟环境
set "VENV_DIR=%SCRIPT_DIR%.venv"
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
    echo 虚拟环境已激活: %VENV_DIR%
) else (
    echo [错误] 未找到虚拟环境 .venv，请先运行: python -m venv .venv
    pause
    exit /b 1
)

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

echo 数据目录: %DATA_ROOT%
echo 存储目录: %STORAGE_DIR%
echo 日志目录: %LOG_DIR%
echo.

:: 启动服务（python -m indexer 调用 indexer/__main__.py）
echo 正在启动 Indexer 服务...
echo 按 Ctrl+C 停止服务
echo.

python -m indexer ^
    --data-root "%DATA_ROOT%" ^
    --storage-dir "%STORAGE_DIR%" ^
    --daemon ^
    --schedule daily:02:00

pause
