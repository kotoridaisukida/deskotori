@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo 请先安装 Python 3，安装时勾选 py launcher。
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo 正在安装依赖，第一次会稍等一会儿...
  py -m venv .venv
  if errorlevel 1 goto fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fail
echo 安装失败。
pause
exit /b 1
