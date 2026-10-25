@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0session-up.bat" 1 %*
exit /b %ERRORLEVEL%
