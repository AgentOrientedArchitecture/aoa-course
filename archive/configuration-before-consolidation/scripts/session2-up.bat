@echo off
setlocal

cd /d "%~dp0.."

call "%~dp0course-mode.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
if "%COURSE_REVISED%"=="1" goto revised

set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"

set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"

docker compose %ENV_ARGS% %LOCAL_ARGS% ^
  -f system/docker-compose.yml ^
  --profile session2 ^
  up --build -d --remove-orphans %*

exit /b %ERRORLEVEL%

:revised
call "%~dp0revised-up.bat" 2 %*
exit /b %ERRORLEVEL%
