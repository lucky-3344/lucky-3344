@echo off
chcp 65001 >nul
setlocal

set "BASE_DIR=%~dp0"
set "PY=python"
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
set "SCRIPT=%BASE_DIR%process_user_file.py"
set "DEFAULT_INPUT=%BASE_DIR%process_input\input.csv"
set "DEFAULT_OUTPUT_DIR=%BASE_DIR%"
set "PROJECT_DIR=%BASE_DIR%"
set "README=%BASE_DIR%README_process_user_file.md"
set "CHEATSHEET=%BASE_DIR%process_user_file_cheatsheet.txt"

:menu
cls
echo ==============================================
echo   坐标批处理 - 快速入口
echo ==============================================
echo.
echo 默认文件:
echo   %DEFAULT_INPUT%
echo.
echo  1. 直接处理默认文件 ^(自动生成 xlsx/csv/kml^)
echo  2. 选择 CSV 文件后处理
echo  3. 打开速查清单
echo  4. 打开完整说明文档
echo  5. 打开最新生成的 KML
echo  0. 退出
echo.
set /p CHOICE=请输入选项(0-5): 

if "%CHOICE%"=="1" goto run_default
if "%CHOICE%"=="2" goto run_pick
if "%CHOICE%"=="3" goto open_cheatsheet
if "%CHOICE%"=="4" goto open_readme
if "%CHOICE%"=="5" goto open_latest_kml
if "%CHOICE%"=="0" goto end
echo.
echo 输入无效，请重新选择。
pause
goto menu

:run_default
echo.
if not exist "%DEFAULT_INPUT%" (
  echo 默认文件不存在:
  echo   %DEFAULT_INPUT%
  echo.
  echo 请改用选项 2 手动选择文件。
  pause
  goto menu
)
echo 正在处理默认文件...
"%PY%" "%SCRIPT%" --cli --input "%DEFAULT_INPUT%" --delay 0.2
echo.
echo 如需查看结果地图，可回到菜单选择 5 打开最新 KML。
pause
goto menu

:run_pick
echo.
echo 将弹出文件选择窗口...
if exist "%BASE_DIR%run_process_cli.bat" (
  call "%BASE_DIR%run_process_cli.bat" --delay 0.2
) else (
  echo 未找到 run_process_cli.bat，请检查文件是否存在。
)
echo.
echo 如需查看结果地图，可回到菜单选择 5 打开最新 KML。
pause
goto menu

:open_cheatsheet
echo.
if exist "%CHEATSHEET%" (
  start "" "%CHEATSHEET%"
) else (
  echo 未找到速查文件:
  echo   %CHEATSHEET%
)
pause
goto menu

:open_latest_kml
echo.
set "LATEST_KML="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$paths = @('%DEFAULT_OUTPUT_DIR%','%PROJECT_DIR%') ^| Where-Object { Test-Path $_ }; $file = Get-ChildItem -Path $paths -Filter 'batch_results_*.kml' -File -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($file){ $file.FullName }"`) do set "LATEST_KML=%%F"

if not defined LATEST_KML (
  echo 未找到 KML 文件。
  echo 请先执行一次批量处理（菜单 1 或 2）。
  pause
  goto menu
)

echo 已找到最新 KML:
echo   %LATEST_KML%
start "" "%LATEST_KML%"
pause
goto menu

:open_readme
echo.
if exist "%README%" (
  start "" "%README%"
) else (
  echo 未找到说明文档:
  echo   %README%
)
pause
goto menu

:end
endlocal
exit /b 0
