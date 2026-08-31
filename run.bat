@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Company Scanner

REM Tim Python: uu tien "py" launcher, sau do "python".
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY (where python >nul 2>&1 && set "PY=python")

if not defined PY (
  echo.
  echo [LOI] Khong tim thay Python tren may.
  echo       Cai tai https://www.python.org/downloads/
  echo       Khi cai nho tick "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0start.py" %*

REM Giu cua so lai de doc duoc loi neu co.
echo.
echo Cua so nay se dong khi ban nhan phim bat ky.
pause >nul
