@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0revised-compose.bat" "%~1"
if errorlevel 1 exit /b %ERRORLEVEL%
if "%SESSION%"=="3" (
  echo Use revised-eve.bat native for authoring, then revised-eve.bat adopt. 1>&2
  exit /b 2
)
shift /1
set "EXTRA_ARGS="
:args
if "%~1"=="" goto run
set EXTRA_ARGS=%EXTRA_ARGS% "%~1"
shift /1
goto args
:run
%COMPOSE% --profile session%SESSION% up --build -d --remove-orphans %EXTRA_ARGS%
exit /b %ERRORLEVEL%
