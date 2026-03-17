@echo off
chcp 65001 >nul
title Build Config Indexer

echo ==========================================
echo   Config Indexer - Build Executable
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "BUILD_DIR=%SCRIPT_DIR%build_temp"

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

:: 复制安装/卸载脚本
copy /y "%SCRIPT_DIR%install.bat" "%DIST_DIR%\install.bat" >nul
copy /y "%SCRIPT_DIR%uninstall.bat" "%DIST_DIR%\uninstall.bat" >nul

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
echo     indexer.exe                可执行文件（双击可手动执行单次构建）
echo     install.bat               安装：首次构建 + 注册每天定时任务
echo     uninstall.bat             卸载：删除定时任务
echo     excel_graph_builder\       运行时依赖
echo.
echo   部署方法:
echo     1. 将 dist\ 整个目录拷贝到 Excel 数据目录下
echo     2. 以管理员身份运行 install.bat（自动首次构建 + 注册定时任务）
echo     3. 完成！之后每天自动构建，无需人工干预
echo.
echo     拷贝后结构:
echo.
echo     excel_data\
echo       excel\                    Excel 表文件
echo       indexer.exe               可执行文件
echo       install.bat               安装定时任务
echo       uninstall.bat             卸载定时任务
echo       excel_graph_builder\      运行时依赖
echo       graph\                    构建产出（自动生成）
echo.
echo ==========================================
pause
