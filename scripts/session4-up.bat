@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0session-up.bat" 4 %*
exit /b %ERRORLEVEL%
