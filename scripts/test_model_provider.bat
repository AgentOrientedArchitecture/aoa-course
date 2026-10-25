@echo off
setlocal EnableExtensions

cd /d "%~dp0.."

if not exist ".env" if not exist ".env.revised" (
  echo error=.env or .env.revised is required in the repository root 1>&2
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo error=Docker Compose v2 is required; run "docker compose version" to diagnose 1>&2
  exit /b 1
)

call "%~dp0compose.bat" 1
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% --profile session1 run --rm --no-deps --build evaluator python -u -m _base.provider_test
exit /b %ERRORLEVEL%
