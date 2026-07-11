@echo off
setlocal

cd /d "%~dp0.."

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"

if not exist "system\agents-eve\workshop\agent\instructions.md" (
  echo No EVE agent exists yet. Run scripts\session3-up.bat and type: eve init .
  exit /b 1
)
if not exist "system\agents-eve\workshop\capability-card.yaml" (
  echo No capability card exists yet. In the workshop shell run:
  echo   cp /adoption-kit/interviewer-questions.yaml capability-card.yaml
  exit /b 1
)

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3-lab-native stop eve-workshop-native >nul 2>&1

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
  --profile session3-lab-wrapped ^
  up --build -d --remove-orphans %*

if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo Your EVE agent is now adopted into AOA.
echo Open http://localhost:8080 and choose: CV fit + interview
echo Registry card: http://localhost:7100/find?id=interviewer-questions
echo Agent card:    http://localhost:7311/.well-known/agent-card.json

exit /b %ERRORLEVEL%
