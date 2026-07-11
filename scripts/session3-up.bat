@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
set "USE_LOCAL_OLLAMA=0"
if /I "%AOA_LOCAL%"=="1" (
  set "LOCAL_ARGS=--profile local"
  set "USE_LOCAL_OLLAMA=1"
)
if /I "%AOA_LOCAL%"=="true" (
  set "LOCAL_ARGS=--profile local"
  set "USE_LOCAL_OLLAMA=1"
)

set "COMPOSE=docker compose %ENV_ARGS% %LOCAL_ARGS% -f system/docker-compose.yml -f system/docker-compose.session3.yml -f system/docker-compose.session3-lab.yml"

rem Native authoring is deliberately isolated from AOA. Remove a previous
rem estate so no stale interviewer card appears during this checkpoint.
%COMPOSE% ^
  --profile session3 ^
  --profile session3-lab-native ^
  --profile session3-lab-wrapped ^
  down --remove-orphans
if errorlevel 1 exit /b %ERRORLEVEL%

%COMPOSE% build eve-workshop-native
if errorlevel 1 exit /b %ERRORLEVEL%

if "%USE_LOCAL_OLLAMA%"=="1" (
  %COMPOSE% up -d ollama
  if errorlevel 1 exit /b 1
)

echo.
echo Opening the native EVE workshop. AOA is not running yet.
echo Use eve init, eve info, and eve dev to build and test the agent.
echo.

%COMPOSE% run --rm --no-deps --service-ports eve-workshop-native
exit /b %ERRORLEVEL%
