@echo off
chcp 65001 >nul
title JEV 刀柄組合判定系統 - 地端伺服器 (公司 Python 版)
cd /d "%~dp0"
echo ========================================================
echo   正在以公司 Python 啟動 JEV 判定系統地端服務...
echo   本機端點: http://localhost:3000
echo ========================================================
start http://localhost:3000
python server.py
pause
