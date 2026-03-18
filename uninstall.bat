@echo off
chcp 65001 >nul

:: ── 自动请求管理员权限 ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 确保工作目录是脚本所在目录
cd /d "%~dp0"

title Excel Graph Builder - 卸载定时任务

:: ============================================================
::   Excel Graph Builder — 卸载定时任务
::
::   删除由 install.bat 注册的 Windows 计划任务
::   不会删除已生成的 graph 数据文件
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "CONFIG_FILE=%SCRIPT_DIR%configs\settings.yml"

:: ── 读取 YAML 获取任务名称 ──
set "TASK_NAME=ExcelGraphBuilder"

if exist "%CONFIG_FILE%" (
    :: 更安全的 YAML 解析，跳过注释行和空行
    setlocal enabledelayedexpansion
    for /f "usebackq delims=" %%a in ("%CONFIG_FILE%") do (
        set "line=%%a"
        :: 跳过空行和注释行
        if not "!line!"=="" (
            set "first_char=!line:~0,1!"
            if not "!first_char!"=="#" (
                :: 使用更精确的解析，只处理包含冒号的行
                for /f "tokens=1,* delims=:" %%b in ("!line!") do (
                    set "_key=%%b"
                    set "_val=%%c"
                    :: 去除键值两端的空格
                    for /f "tokens=*" %%k in ("!_key!") do set "_key=%%k"
                    if defined _val for /f "tokens=*" %%v in ("!_val!") do set "_val=%%v"
                    if "!_key!"=="task_name" set "_TN=!_val!"
                )
            )
        )
    )
    endlocal & if defined _TN set "TASK_NAME=%_TN%"
)

echo ==========================================
echo   Excel Graph Builder - 卸载
echo ==========================================
echo.
echo   将删除计划任务: %TASK_NAME%
echo   已生成的 graph\ 数据不会被删除
echo.

schtasks /Delete /TN "%TASK_NAME%" /F

if errorlevel 1 (
    echo.
    echo [提示] 任务不存在，或需要管理员权限运行
) else (
    echo.
    echo [成功] 定时任务已卸载，不再自动执行构建
)

echo.
pause
