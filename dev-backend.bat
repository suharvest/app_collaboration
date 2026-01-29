@echo off
chcp 65001 >nul
title Backend [3260]
cd /d %~dp0

set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo ==========================================
echo   Backend Dev Server - http://localhost:3260
echo ==========================================
echo.

uv run uvicorn provisioning_station.main:app --host 0.0.0.0 --port 3260 --log-level info --reload
