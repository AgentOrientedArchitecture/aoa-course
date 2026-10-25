@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0compose.bat" 1
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% --profile "*" logs -f --tail=100 %*
exit /b %ERRORLEVEL%
