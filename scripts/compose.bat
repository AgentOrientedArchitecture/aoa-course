@echo off
rem Shared current-course configuration; called without setlocal so the caller inherits it.
cd /d "%~dp0.."
set "SESSION=%~1"
set "ENV_ARGS="
if exist ".env" set "ENV_ARGS=--env-file .env"
if exist ".env.revised" set "ENV_ARGS=%ENV_ARGS% --env-file .env.revised"
set "LOCAL_ARGS="
if /I "%AOA_LOCAL%"=="1" set "LOCAL_ARGS=--profile local"
if /I "%AOA_LOCAL%"=="true" set "LOCAL_ARGS=--profile local"
set "FILES=-f system/docker-compose.yml"
set "COURSE_PLANNER_STRATEGY="
set "COURSE_PLAN_GOVERNANCE_CAPABILITY="
set "COURSE_ALLOW_WIKI_RESET=true"
set "COURSE_REPORTER_ALLOWLIST="
if "%SESSION%"=="1" goto session1
if "%SESSION%"=="2" goto session2
if "%SESSION%"=="3" goto session3
if "%SESSION%"=="4" goto session4
echo Choose session 1, 2, 3 or 4. 1>&2
exit /b 2
:session1
set "COURSE_STUDIO_WORKFLOWS=cv-fit"
set "COURSE_REPORTER_ALLOWLIST=reporter-cv-fit"
set "COURSE_REGISTRY_ALLOWLIST=tool-document-text,parser-cv,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,reporter-cv-fit"
set "COURSE_EVALUATOR_ALLOWLIST=evaluator-cv"
goto finish
:session2
set "COURSE_STUDIO_WORKFLOWS=cv-fit,knowledge-ingest,wiki-graph,knowledge-query"
if defined STUDIO_WORKFLOWS set "COURSE_STUDIO_WORKFLOWS=%STUDIO_WORKFLOWS%"
set "COURSE_REGISTRY_ALLOWLIST=tool-filesystem,tool-document-text,tool-wiki-store,parser-cv,parser-notes,parser-query,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,evaluator-promote,evaluator-wiki-query,reporter-cv-fit,reporter-ingest-summary,reporter-answer"
set "COURSE_EVALUATOR_ALLOWLIST=evaluator-cv,evaluator-promote,evaluator-wiki-query"
goto finish
:session3
set "COURSE_STUDIO_WORKFLOWS=cv-fit,cv-fit-interview"
set "COURSE_PLANNER_STRATEGY=deterministic"
set "COURSE_REPORTER_ALLOWLIST=reporter-cv-fit"
set "COURSE_REGISTRY_ALLOWLIST=tool-document-text,parser-cv,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,reporter-cv-fit,interviewer-questions"
set "COURSE_EVALUATOR_ALLOWLIST=evaluator-cv"
goto finish
:session4
set "COURSE_STUDIO_WORKFLOWS=agent-card-check,cv-fit,flow-audit,wiki-graph,knowledge-query"
set "COURSE_PLANNER_STRATEGY=deterministic"
set "COURSE_PLAN_GOVERNANCE_CAPABILITY=evaluator-plan-governance"
set "COURSE_ALLOW_WIKI_RESET=false"
set "COURSE_REPORTER_ALLOWLIST=reporter-cv-fit,reporter-answer,reporter-agent-evidence,reporter-flow-audit"
set "COURSE_REGISTRY_ALLOWLIST=tool-filesystem,tool-document-text,tool-wiki-store,parser-cv,parser-query,parser-estate,evaluator-cv,evaluator-wiki-query,evaluator-plan-governance,evaluator-agent-evidence,evaluator-flow-evidence,reporter-cv-fit,reporter-answer,reporter-agent-evidence,reporter-flow-audit"
set "COURSE_EVALUATOR_ALLOWLIST=evaluator-cv,evaluator-wiki-query,evaluator-plan-governance,evaluator-agent-evidence,evaluator-flow-evidence"
:finish
set "COURSE_DISCOVERY_BACKEND=local"
if "%SESSION%"=="3" set "COURSE_DISCOVERY_BACKEND=agntcy"
if "%SESSION%"=="4" set "COURSE_DISCOVERY_BACKEND=agntcy"
set "DIRECTORY_ARGS="
if "%COURSE_DISCOVERY_BACKEND%"=="agntcy" set "DIRECTORY_ARGS=--profile directory"
set "COURSE_DIRECTORY_EXPECTED_AUS=%COURSE_REGISTRY_ALLOWLIST:tool-document-text,=%"
set "COURSE_DIRECTORY_EXPECTED_AUS=%COURSE_DIRECTORY_EXPECTED_AUS:tool-filesystem,=%"
set "COURSE_DIRECTORY_EXPECTED_AUS=%COURSE_DIRECTORY_EXPECTED_AUS:tool-wiki-store,=%"
set "COMPOSE=docker compose %ENV_ARGS% %LOCAL_ARGS% %DIRECTORY_ARGS% %FILES%"
exit /b 0
