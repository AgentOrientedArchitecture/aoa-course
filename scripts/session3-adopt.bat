@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0eve-workshop.bat" adopt %*
exit /b %ERRORLEVEL%
