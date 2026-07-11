@echo off
setlocal

cd /d "%~dp0.."

if exist "system\agents-eve\workshop\agent" (
  echo The Session 3 EVE agent already exists.
  echo Continue with the lab, or remove system\agents-eve\workshop\agent to start again.
  exit /b 1
)

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  build eve-workshop-native
if errorlevel 1 exit /b %ERRORLEVEL%

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  run --rm --no-deps -e AI_AGENT=course-scaffold ^
  eve-workshop-native /app/node_modules/.bin/eve init .

exit /b %ERRORLEVEL%
