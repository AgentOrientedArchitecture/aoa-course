@echo off
setlocal EnableExtensions

cd /d "%~dp0.."

if not exist ".env" (
  echo error=.env not found in the repository root 1>&2
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo error=Docker Compose v2 is required; run "docker compose version" to diagnose 1>&2
  exit /b 1
)

docker compose ^
  --env-file .env ^
  -f system/docker-compose.yml ^
  --profile session1 ^
  run --rm --no-deps --build ^
  evaluator python -u -m _base.provider_test

exit /b %ERRORLEVEL%
