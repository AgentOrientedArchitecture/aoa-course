@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0eve-workshop.bat" build %*
exit /b %ERRORLEVEL%
