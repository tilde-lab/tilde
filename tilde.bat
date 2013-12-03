:: Tilde project: entry point for Windows environment
:: See http://tilde.pro

@echo off
set CUR=%~dp0
"%CUR%\\windows\\python\\python.exe" "%CUR%\\core\\cli.py" %*
pause > nul
