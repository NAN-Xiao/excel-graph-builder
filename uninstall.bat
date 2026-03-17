@echo off
chcp 65001 >nul
title Excel Graph Builder - 卸载定时任务

:: ============================================================
::   Excel Graph Builder — 卸载定时任务
::
::   删除由 install.bat 注册的 Windows 计划任务
::   不会删除已生成的 graph 数据文件
::
::   注意: 需要管理员权限
:: ============================================================

set "TASK_NAME=ExcelGraphBuilder"

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
