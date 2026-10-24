@echo off
rem Called after changing to the repository root. Keep variables in the caller.
set "COURSE_REVISED=0"
if /I "%AOA_REVISED%"=="1" goto revised
if /I "%AOA_REVISED%"=="true" goto revised
if /I "%AOA_REVISED%"=="0" exit /b 0
if /I "%AOA_REVISED%"=="false" exit /b 0
if not defined AOA_REVISED goto auto
if /I "%AOA_REVISED%"=="auto" goto auto
echo AOA_REVISED must be auto, 1/true or 0/false. 1>&2
exit /b 2
:auto
if not exist ".env.revised" exit /b 0
:revised
set "COURSE_REVISED=1"
exit /b 0
