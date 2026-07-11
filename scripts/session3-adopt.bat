@echo off
rem Publish the learner-authored EVE agent into AOA and start the intent surface.
call "%~dp0session3-lab-wrap.bat" %*
exit /b %ERRORLEVEL%
