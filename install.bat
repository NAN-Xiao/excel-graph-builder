@echo off
chcp 65001 >nul

:: ── 自动请求管理员权限 ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 确保工作目录是脚本所在目录（UAC 提权后默认在 System32）
cd /d "%~dp0"

title Excel Graph Builder - 安装定时任务

:: ============================================================
::   Excel Graph Builder — 安装定时任务
::
::   执行内容：
::     1. 立即执行一次增量构建（确认环境正常）
::     2. 注册 Windows 计划任务，每天定时自动构建
::
::   配置文件: configs\settings.yml
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%indexer.exe"
set "CONFIG_FILE=%SCRIPT_DIR%configs\settings.yml"

:: 检查 exe
if not exist "%EXE_PATH%" (
    echo [错误] 未找到 indexer.exe
    echo   请确认 install.bat 与 indexer.exe 在同一目录
    pause
    exit /b 1
)

:: 检查配置文件
if not exist "%CONFIG_FILE%" (
    echo [错误] 未找到配置文件 configs\settings.yml
    pause
    exit /b 1
)

:: ── 读取 YAML 配置 ──
set "TASK_NAME=ExcelGraphBuilder"
set "SCHEDULE_TIME=02:00"
set "GRAPH_DIR=..\graph"

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
                if "!_key!"=="schedule_time" set "_ST=!_val!"
                if "!_key!"=="graph_dir" set "_GD=!_val!"
            )
        )
    )
)
endlocal & (
    if defined _TN set "TASK_NAME=%_TN%"
    if defined _ST set "SCHEDULE_TIME=%_ST%"
    if defined _GD set "GRAPH_DIR=%_GD%"
)

for %%i in ("%SCRIPT_DIR%%GRAPH_DIR%") do set "GRAPH_DIR_ABS=%%~fi"
set "SCHEMA_GRAPH_FILE=%GRAPH_DIR_ABS%\schema_graph.json"

echo ==========================================
echo   Excel Graph Builder - 安装
echo ==========================================
echo.
echo   配置文件: %CONFIG_FILE%
echo   构建目录: %GRAPH_DIR_ABS%
echo.

:: ── Step 1: 仅在未构建时执行首次构建 ──
if exist "%SCHEMA_GRAPH_FILE%" (
    echo [1/2] 检测到现有构建，跳过首次构建
    echo   已存在: %SCHEMA_GRAPH_FILE%
) else (
    echo [1/2] 未检测到构建产物，执行首次构建...
    echo.

    "%EXE_PATH%" --config "%CONFIG_FILE%" --run-now

    if errorlevel 1 (
        echo.
        echo [警告] 首次构建可能未完全成功，但将继续注册定时任务
        echo.
    )
)

:: ── Step 2: 注册 Windows 计划任务 ──
echo.
echo [2/2] 注册 Windows 计划任务...
echo   任务名称: %TASK_NAME%
echo   执行时间: 每天 %SCHEDULE_TIME%
echo.

:: 删除已有同名任务
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

:: 创建计划任务（仍使用 schtasks；由 PowerShell 负责可靠拼接 /TR 参数）
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$tr = '\"' + $env:EXE_PATH + '\" --config \"' + $env:CONFIG_FILE + '\" --run-now';" ^
    "schtasks /Create /TN $env:TASK_NAME /TR $tr /SC DAILY /ST $env:SCHEDULE_TIME /RL HIGHEST /F;" ^
    "exit $LASTEXITCODE"

if errorlevel 1 (
    echo.
    echo [错误] 计划任务注册失败！
    echo   请以管理员身份运行此脚本（右键 → 以管理员身份运行）
    echo.
    echo   首次构建已完成，手动执行请双击 indexer.exe
    pause
    exit /b 1
)

:: 二次校验：确认任务实际已创建
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 计划任务创建后未能查询到！
    echo   任务名=%TASK_NAME%
    echo   请手动执行以下命令排查：
    echo     schtasks /Query /TN "%TASK_NAME%" /V /FO LIST
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
if exist "%SCHEMA_GRAPH_FILE%" (
    echo   图谱状态: 已存在构建产物
) else (
    echo   图谱状态: 尚未检测到 schema_graph.json
)
echo   定时任务: 每天 %SCHEDULE_TIME% 自动执行
echo.
echo   手动触发: schtasks /Run /TN "%TASK_NAME%"
echo   卸载任务: 运行 uninstall.bat
echo.
echo ==========================================
pause
