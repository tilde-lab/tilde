:: Tilde project: entry point for Windows environment
:: See http://wwwtilda.googlecode.com

@echo off
set CUR=%~dp0
"%CUR%\\windows\\python\\python.exe" "%CUR%\\core\\tilde.py" %*
pause > nul
