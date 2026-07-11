@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"

if not exist "system\agents-eve\workshop\agent\instructions.md" (
  echo No EVE agent exists yet. Run scripts\session3-lab-init.bat first.
  exit /b 1
)

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3-lab-wrapped stop eve-workshop-wrapped >nul 2>&1

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3-reference stop eve-interviewer >nul 2>&1

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3 ^
  --profile session3-lab-native ^
  up --build -d --remove-orphans %*

exit /b %ERRORLEVEL%
