@echo off
setlocal
cd /d "%~dp0.."

call "%~dp0course-mode.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
if "%COURSE_REVISED%"=="1" goto revised

set COMPOSE=docker compose
if exist .env set COMPOSE=%COMPOSE% --env-file .env
if /i "%AOA_LOCAL%"=="1" set COMPOSE=%COMPOSE% --profile local
if /i "%AOA_LOCAL%"=="true" set COMPOSE=%COMPOSE% --profile local

%COMPOSE% -f system/docker-compose.yml -f system/docker-compose.session4.yml --profile session4 up --build -d --remove-orphans %*

exit /b %ERRORLEVEL%

:revised
call "%~dp0revised-up.bat" 4 %*
exit /b %ERRORLEVEL%
