@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0session-up.bat" 2 %*
exit /b %ERRORLEVEL%
