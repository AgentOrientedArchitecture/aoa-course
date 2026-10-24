@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "MODE=%~1"
if not defined MODE set "MODE=native"
call "%~dp0revised-compose.bat" 3
if errorlevel 1 exit /b %ERRORLEVEL%
shift
set "EXTRA_ARGS="
:args
if "%~1"=="" goto dispatch
set EXTRA_ARGS=%EXTRA_ARGS% "%~1"
shift
goto args
:dispatch
if /I "%MODE%"=="build" goto build
if /I "%MODE%"=="native" goto native
if /I "%MODE%"=="adopt" goto adopt
echo Usage: revised-eve.bat build^|native^|adopt 1>&2
exit /b 2
:build
%COMPOSE% --profile session3 --profile session3-lab-native --profile session3-lab-wrapped build %EXTRA_ARGS%
exit /b %ERRORLEVEL%
:native
call "%~dp0down.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% build eve-workshop-native
if errorlevel 1 exit /b %ERRORLEVEL%
if defined LOCAL_ARGS (
  %COMPOSE% up -d ollama
  if errorlevel 1 exit /b 1
)
%COMPOSE% run --rm --no-deps --service-ports -e HOME=/tmp %EXTRA_ARGS% eve-workshop-native
exit /b %ERRORLEVEL%
:adopt
set "WORKSPACE=system\agents-eve\workshop"
if not exist "%WORKSPACE%\agent\agent.ts" goto missing
if not exist "%WORKSPACE%\agent\instructions.md" goto missing
if not exist "%WORKSPACE%\agent\channels\eve.ts" goto missing
if not exist "%WORKSPACE%\capability-card.yaml" (
  copy /Y system\agents-eve\runtime\templates\interviewer-questions.yaml "%WORKSPACE%\capability-card.yaml" >nul
  if errorlevel 1 exit /b 1
)
%COMPOSE% build eve-workshop-native
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% run --rm --no-deps -e HOME=/tmp eve-workshop-native npm install --offline --no-audit --no-fund
if errorlevel 1 exit /b %ERRORLEVEL%
%COMPOSE% --profile session3 --profile session3-lab-wrapped up --build --force-recreate -d --remove-orphans %EXTRA_ARGS%
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0eve-ready.bat"
exit /b %ERRORLEVEL%
:missing
echo Complete native EVE authoring under %WORKSPACE% before adoption. 1>&2
exit /b 1
