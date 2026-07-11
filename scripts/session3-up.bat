@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"

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
  build eve-workshop-native
if errorlevel 1 exit /b %ERRORLEVEL%

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3 ^
  up --build -d --remove-orphans
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo AOA is running at http://localhost:8080.
echo Opening the interactive EVE workshop container...
echo.

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  run --rm --no-deps --service-ports eve-workshop-native

exit /b %ERRORLEVEL%
