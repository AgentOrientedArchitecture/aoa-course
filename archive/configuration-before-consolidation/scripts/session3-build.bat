@echo off
rem Pre-build Session 3 images without starting services or creating the agent.
setlocal

cd /d "%~dp0.."

call "%~dp0course-mode.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
if "%COURSE_REVISED%"=="1" goto revised

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

docker compose %ENV_ARGS% ^
  -f system/docker-compose.yml ^
  -f system/docker-compose.session3.yml ^
  -f system/docker-compose.session3-lab.yml ^
  --profile session3 ^
  --profile session3-lab-native ^
  build %*

exit /b %ERRORLEVEL%

:revised
call "%~dp0revised-eve.bat" build %*
exit /b %ERRORLEVEL%
