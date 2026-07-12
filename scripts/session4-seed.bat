@echo off
rem Seed the wiki store with the EU AI Act regulations corpus for Session 4.
rem Deterministic (no LLM): posts pre-baked promotion sidecars directly to the
rem wiki-store bridge. Requires only Windows PowerShell, included with Windows.
setlocal EnableExtensions

cd /d "%~dp0.."

set "SEED_DIR=course\data\session-04-compliance\regulations-seed"
set "INBOX_DIR=system\inbox\regulations"
set "BRIDGE_BASE=%WIKI_STORE_URL%"
if not defined BRIDGE_BASE set "BRIDGE_BASE=http://localhost:7403"
set "BRIDGE_URL=%BRIDGE_BASE%/invoke?capability=tool-wiki-store"

if not exist "%SEED_DIR%" (
  echo Seed directory not found: %SEED_DIR%
  exit /b 1
)

if not exist "%INBOX_DIR%" mkdir "%INBOX_DIR%"
if errorlevel 1 exit /b %ERRORLEVEL%

copy /Y "%SEED_DIR%\*.md" "%INBOX_DIR%\" >nul
if errorlevel 1 exit /b %ERRORLEVEL%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$seedDir = $env:SEED_DIR;" ^
  "$bridge = $env:BRIDGE_URL;" ^
  "$count = 0;" ^
  "Get-ChildItem -LiteralPath $seedDir -Filter '*.promotion.json' | Sort-Object Name | ForEach-Object {" ^
  "  $sidecar = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json;" ^
  "  $body = @{ inputs = @{ op = 'write_ingest'; promotion = $sidecar.promotion; source_path = ('/data/inbox/regulations/' + $sidecar.source_file) } } | ConvertTo-Json -Depth 100;" ^
  "  $result = Invoke-RestMethod -Method Post -Uri $bridge -ContentType 'application/json' -Body $body -TimeoutSec 30;" ^
  "  $stored = $result.outputs.stored;" ^
  "  $documentId = if ($null -ne $stored.document_id) { $stored.document_id } else { '?' };" ^
  "  $passageCount = if ($null -ne $stored.passage_count) { $stored.passage_count } else { 0 };" ^
  "  Write-Host ('seeded ' + $documentId + ' (' + $passageCount + ' passages)');" ^
  "  $count++;" ^
  "};" ^
  "Write-Host ('done: ' + $count + ' regulation notes in the wiki store');"

exit /b %ERRORLEVEL%
