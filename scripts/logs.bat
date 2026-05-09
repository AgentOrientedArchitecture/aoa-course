@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session2.yml ^
  --profile session2 ^
  --profile session4 ^
  logs -f --tail=100 %*

exit /b %ERRORLEVEL%
