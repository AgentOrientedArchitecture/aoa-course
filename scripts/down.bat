@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0compose.bat" 1
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% --profile "*" down --remove-orphans %*
exit /b %ERRORLEVEL%
