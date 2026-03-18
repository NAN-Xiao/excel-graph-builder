@echo off
chcp 65001 >nul
title Build Config Indexer

echo ==========================================
echo   Config Indexer - Build Executable
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "DIST_DIR=%SCRIPT_DIR%..\dist"
set "BUILD_DIR=%SCRIPT_DIR%build_temp"
set "COPY_VENV=0"

:: 解析参数：build.bat venv 可将 .venv 一并拷贝到 dist
for %%a in (%*) do (
    if /i "%%a"=="venv" set "COPY_VENV=1"
)

:: 激活虚拟环境
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo [错误] 未找到虚拟环境 .venv
    echo 请先运行: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: 确保 PyInstaller 已安装
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

echo.
echo [1/3] 清理旧构建...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

echo [2/3] 正在构建可执行程序...
echo.

pyinstaller ^
    --name indexer ^
    --distpath "%DIST_DIR%\pack" ^
    --workpath "%BUILD_DIR%" ^
    --specpath "%BUILD_DIR%" ^
    --noconfirm ^
    --clean ^
    --console ^
    --onedir ^
    --contents-directory excel_graph_builder ^
    --hidden-import=indexer ^
    --hidden-import=indexer.service ^
    --hidden-import=indexer.core ^
    --hidden-import=indexer.core.builder ^
    --hidden-import=indexer.core.config ^
    --hidden-import=indexer.scanner ^
    --hidden-import=indexer.scanner.excel_reader ^
    --hidden-import=indexer.scanner.schema_extractor ^
    --hidden-import=indexer.scanner.directory_scanner ^
    --hidden-import=indexer.discovery ^
    --hidden-import=indexer.discovery.containment ^
    --hidden-import=indexer.discovery.naming_convention ^
    --hidden-import=indexer.discovery.abbreviation ^
    --hidden-import=indexer.discovery.transitive ^
    --hidden-import=indexer.discovery.feedback ^
    --hidden-import=indexer.discovery.game_dictionary ^
    --hidden-import=indexer.discovery.value_utils ^
    --hidden-import=indexer.export ^
    --hidden-import=indexer.export.llm_chunks ^
    --hidden-import=indexer.export.rag_assets ^
    --hidden-import=indexer.export.cell_locator ^
    --hidden-import=indexer.export.atomic_write ^
    --hidden-import=indexer.analysis ^
    --hidden-import=indexer.analysis.analyzer ^
    --hidden-import=indexer.report ^
    --hidden-import=indexer.report.html_generator ^
    --hidden-import=indexer.storage ^
    --hidden-import=indexer.storage.json_storage ^
    --hidden-import=indexer.scheduler ^
    --hidden-import=indexer.watcher ^
    --hidden-import=indexer.models ^
    --collect-submodules=indexer ^
    indexer\__main__.py

if errorlevel 1 (
    echo.
    echo [错误] 构建失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 整理发布目录...

:: 将 PyInstaller 输出扁平化到 dist 根目录
move "%DIST_DIR%\pack\indexer\indexer.exe" "%DIST_DIR%\indexer.exe" >nul
move "%DIST_DIR%\pack\indexer\excel_graph_builder" "%DIST_DIR%\excel_graph_builder" >nul

:: 复制脚本和配置文件
xcopy /y /i /e "%SCRIPT_DIR%configs" "%DIST_DIR%\configs" >nul
copy /y "%SCRIPT_DIR%install.bat" "%DIST_DIR%\install.bat" >nul
copy /y "%SCRIPT_DIR%uninstall.bat" "%DIST_DIR%\uninstall.bat" >nul

:: 可选：拷贝 .venv（build.bat venv）
if "%COPY_VENV%"=="1" (
    echo   拷贝 .venv 到发布目录...
    xcopy /y /i /e /q "%VENV_DIR%" "%DIST_DIR%\.venv" >nul
    echo   .venv 拷贝完成
)

:: 清理中间目录
rmdir /s /q "%DIST_DIR%\pack" 2>nul
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

echo.
echo ==========================================
echo   构建完成！
echo ==========================================
echo.
echo   发布目录: %DIST_DIR%\
echo.
echo   dist\
echo     indexer.exe                可执行文件
echo     configs\settings.yml      配置文件（部署时按需修改）
echo     install.bat               安装：首次构建 + 注册定时任务
echo     uninstall.bat             卸载：删除定时任务
echo     excel_graph_builder\       运行时依赖
if "%COPY_VENV%"=="1" echo     .venv\                    Python 虚拟环境
echo.
echo   构建产出已放置在上级目录:
echo.
echo     excel_data\               根目录
echo       dist\                   部署包（已就绪）
echo       excel\                  Excel 表文件
echo       graph\                  构建产出（install 后自动生成）
echo.
echo   下一步:
echo     1. 按需编辑 dist\configs\settings.yml
echo     2. 以管理员身份运行 dist\install.bat
echo.
echo ==========================================
pause
