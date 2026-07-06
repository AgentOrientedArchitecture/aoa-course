@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session1.yml ^
  --profile session1 ^
  --profile session2 ^
  --profile session3 ^
  down --remove-orphans %*

exit /b %ERRORLEVEL%
