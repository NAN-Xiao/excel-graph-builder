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

:: 复制启动脚本
copy /y "%SCRIPT_DIR%indexer_run.bat" "%DIST_DIR%\indexer_run.bat" >nul

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
echo     indexer_run.bat            双击启动（增量构建）
echo     excel_graph_builder\       运行时依赖
echo.
echo   部署方法:
echo     将 dist\ 目录下所有内容拷贝到 Excel 数据目录下即可。
echo     拷贝后结构:
echo.
echo     excel_data\
echo       configs\                  Excel 表文件
echo       indexer.exe               直接双击或命令行运行
echo       indexer_run.bat           双击启动
echo       excel_graph_builder\      运行时依赖
echo       graph\                    构建产出（自动生成）
echo.
echo ==========================================
pause
