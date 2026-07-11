@echo off
rem Adopt the learner-authored EVE agent into AOA and start the intent surface.
setlocal EnableExtensions

cd /d "%~dp0.."

set "WORKSPACE=system\agents-eve\workshop"
set "TEMPLATE=system\agents-eve\runtime\templates\interviewer-questions.yaml"
set "CARD=%WORKSPACE%\capability-card.yaml"

if not exist "%WORKSPACE%\agent\agent.ts" goto missing_agent
if not exist "%WORKSPACE%\agent\instructions.md" goto missing_agent
if not exist "%WORKSPACE%\agent\channels\eve.ts" goto missing_agent

set "CARD_CREATED=0"
if not exist "%CARD%" (
  copy /Y "%TEMPLATE%" "%CARD%" >nul
  if errorlevel 1 exit /b 1
  set "CARD_CREATED=1"
)

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"

set "COMPOSE=docker compose %ENV_ARGS% %LOCAL_ARGS% -f system/docker-compose.yml -f system/docker-compose.session3.yml -f system/docker-compose.session3-lab.yml"

%COMPOSE% ^
  --profile session3 ^
  --profile session3-lab-wrapped ^
  up --build --force-recreate -d --remove-orphans %*
if errorlevel 1 exit /b %ERRORLEVEL%

set "READY=0"
for /L %%I in (1,1,120) do (
  curl --fail --silent --output nul "http://localhost:7311/healthz" >nul 2>&1
  if not errorlevel 1 (
    set "READY=1"
    goto ready
  )
  ping 127.0.0.1 -n 2 >nul
)

:ready
if "%READY%"=="0" (
  echo AOA started, but the adopted EVE agent was not healthy within 120 seconds.
  echo Run scripts\logs.bat eve-workshop-wrapped registry to inspect the failure.
  exit /b 1
)

curl --fail --silent --output nul "http://localhost:7100/find?id=interviewer-questions" >nul 2>&1
if errorlevel 1 (
  echo The adopted EVE agent is healthy, but interviewer-questions is absent from the registry.
  echo Run scripts\logs.bat eve-workshop-wrapped registry to inspect the failure.
  exit /b 1
)

echo.
if "%CARD_CREATED%"=="1" (
  echo Created AOA contract: %CARD%
) else (
  echo Using existing AOA contract: %CARD%
)
echo.
echo Your EVE agent is now adopted into AOA.
echo Added by adoption:
echo   Agent ID: urn:aoa:agent:eve-workshop-interviewer
echo   Registry lifecycle and discovery
echo   Outward A2A endpoint and trace boundary
echo   Model provenance and skills_hash
echo.
echo The EVE-authored agent files were not changed.
echo Open http://localhost:8080 and choose: CV fit + interview
echo Registry card: http://localhost:7100/find?id=interviewer-questions
echo Agent card:    http://localhost:7311/.well-known/agent-card.json
exit /b 0

:missing_agent
echo Missing one or more EVE agent files under %WORKSPACE%\agent.
echo Run scripts\session3-up.bat, then create and test the agent with eve init and eve dev.
exit /b 1
