@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0.."
set "MODE=%~1"
if not defined MODE set "MODE=help"
shift /1
set "EXTRA_ARGS="
:args
if "%~1"=="" goto dispatch
set EXTRA_ARGS=%EXTRA_ARGS% "%~1"
shift /1
goto args
:dispatch
set "COMPOSE=docker compose -f system/docker-compose.directory.yml --profile directory"
if /I "%MODE%"=="up" goto up
if /I "%MODE%"=="start" goto up
if /I "%MODE%"=="stop" goto stop
if /I "%MODE%"=="logs" goto logs
if /I "%MODE%"=="cli" goto cli
for %%C in (export push search pull check sync) do if /I "%MODE%"=="%%C" goto helper
if /I "%MODE%"=="help" goto help
if /I "%MODE%"=="--help" goto help
echo Unknown Directory command. Use directory.bat help. 1>&2
exit /b 2
:up
if not exist ".course-data" mkdir ".course-data"
if not exist ".course-data" exit /b 1
%COMPOSE% up --build -d --wait --wait-timeout 120 %EXTRA_ARGS% agntcy-directory
exit /b %ERRORLEVEL%
:stop
%COMPOSE% stop %EXTRA_ARGS% agntcy-directory
exit /b %ERRORLEVEL%
:logs
%COMPOSE% logs -f --tail=100 %EXTRA_ARGS% agntcy-directory
exit /b %ERRORLEVEL%
:cli
%COMPOSE% exec -T agntcy-directory dirctl --server-addr 127.0.0.1:8890 --auth-mode insecure %EXTRA_ARGS%
exit /b %ERRORLEVEL%
:helper
%COMPOSE% exec -T agntcy-directory python /app/directory-lab.py %MODE% %EXTRA_ARGS%
exit /b %ERRORLEVEL%
:help
echo Usage: directory.bat up^|stop^|logs^|export^|push^|search^|pull^|check^|sync^|cli [arguments]
exit /b 0
