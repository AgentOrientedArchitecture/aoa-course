@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session1.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  -f system/docker-compose.session4.yml ^
  --profile session1 ^
  --profile session2 ^
  --profile session3 ^
  --profile session3-lab-native ^
  --profile session3-lab-wrapped ^
  --profile session4 ^
  --profile local ^
  logs -f --tail=100 %*

exit /b %ERRORLEVEL%
