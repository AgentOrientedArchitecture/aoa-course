@echo off
setlocal
for /L %%I in (1,1,120) do (
  curl --fail --silent --output nul http://localhost:7311/healthz >nul 2>&1
  if not errorlevel 1 goto registered
  ping 127.0.0.1 -n 2 >nul
)
echo The adopted EVE agent was not healthy within 120 seconds. Inspect scripts\logs.bat eve-workshop-wrapped registry. 1>&2
exit /b 1
:registered
curl --fail --silent --output nul "http://localhost:7100/find?id=interviewer-questions" >nul 2>&1
if errorlevel 1 (
  echo EVE is healthy but interviewer-questions is absent from the registry. 1>&2
  exit /b 1
)
echo EVE adopted and registered. Open http://localhost:8080 and choose CV fit + interview.
exit /b 0
