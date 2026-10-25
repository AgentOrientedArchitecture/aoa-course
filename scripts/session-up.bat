@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0compose.bat" "%~1"
if errorlevel 1 exit /b %ERRORLEVEL%
if "%SESSION%"=="3" (
  echo Use eve-workshop.bat native for authoring, then eve-workshop.bat adopt. 1>&2
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
if "%SESSION%"=="4" if not exist ".course-data" mkdir ".course-data"
%COMPOSE% --profile session%SESSION% up --build -d --remove-orphans %EXTRA_ARGS%
if errorlevel 1 exit /b %ERRORLEVEL%
if "%SESSION%"=="4" call "%~dp0directory.bat" sync --wait 120
exit /b %ERRORLEVEL%
