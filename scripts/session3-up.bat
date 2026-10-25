@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0eve-workshop.bat" native %*
exit /b %ERRORLEVEL%
