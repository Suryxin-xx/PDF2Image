@echo off
chcp 65001 >nul
title PDF2Image Release Builder

powershell.exe -NoProfile -NoLogo -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1"

echo.
if errorlevel 1 (
    echo 打包脚本执行失败，错误代码：%errorlevel%
) else (
    echo 打包脚本执行完成。
)

echo.
pause