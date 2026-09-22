@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "启动底版.py"
) else (
  python "启动底版.py"
)
if errorlevel 1 (
  echo 请把这个文件夹交给WorkBuddy，让它检查Python环境并打开工作台。
  pause
)
