@echo off
rem Seed and verify the inspectable EU AI Act governance/evidence corpus.
rem Deterministic (no LLM): post pre-baked promotion sidecars to tool-wiki-store.
rem Requires only Windows PowerShell, included with Windows.
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

echo Loading corpus: curated EU AI Act Session 4 regulations from %SEED_DIR%
if not exist "%INBOX_DIR%" mkdir "%INBOX_DIR%"
if errorlevel 1 exit /b %ERRORLEVEL%

copy /Y "%SEED_DIR%\*.md" "%INBOX_DIR%\" >nul
if errorlevel 1 exit /b %ERRORLEVEL%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$seedDir = $env:SEED_DIR;" ^
  "$bridge = $env:BRIDGE_URL;" ^
  "function Invoke-WikiStore([hashtable] $Inputs) {" ^
  "  $body = @{ inputs = $Inputs } | ConvertTo-Json -Depth 100;" ^
  "  $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body);" ^
  "  Invoke-RestMethod -Method Post -Uri $bridge -ContentType 'application/json; charset=utf-8' -Body $bodyBytes -TimeoutSec 30;" ^
  "};" ^
  "$count = 0;" ^
  "Get-ChildItem -LiteralPath $seedDir -Filter '*.promotion.json' | Sort-Object Name | ForEach-Object {" ^
  "  $sidecar = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json;" ^
  "  $result = Invoke-WikiStore @{ op = 'write_ingest'; promotion = $sidecar.promotion; source_path = ('/data/inbox/regulations/' + $sidecar.source_file) };" ^
  "  $stored = $result.outputs.stored;" ^
  "  $documentId = if ($null -ne $stored.document_id) { $stored.document_id } else { '?' };" ^
  "  $passageCount = if ($null -ne $stored.passage_count) { $stored.passage_count } else { 0 };" ^
  "  Write-Host ('seeded ' + $documentId + ' (' + $passageCount + ' passages)');" ^
  "  $count++;" ^
  "};" ^
  "Write-Host ('loaded: ' + $count + ' regulation notes into the wiki store');" ^
  "$missing = $false;" ^
  "foreach ($query in @('annex iii high-risk employment recruitment selection evaluate candidates', 'article 14 human oversight natural persons effectively overseen')) {" ^
  "  Write-Host ('query: ' + $query);" ^
  "  $result = Invoke-WikiStore @{ op = 'search'; query = $query; limit = 1 };" ^
  "  $passages = @($result.outputs.passages | Where-Object { $null -ne $_ });" ^
  "  if ($passages.Count -eq 0) {" ^
  "    Write-Error ('FAILED: no wiki passage found for query: ' + $query);" ^
  "    $missing = $true;" ^
  "    continue;" ^
  "  };" ^
  "  $top = $passages[0];" ^
  "  $passageId = [string] $top.passage_id;" ^
  "  $source = [string] $top.source_path;" ^
  "  if ([string]::IsNullOrWhiteSpace($passageId) -or [string]::IsNullOrWhiteSpace($source)) {" ^
  "    Write-Error ('FAILED: top wiki passage lacks passage_id or source_path for query: ' + $query);" ^
  "    $missing = $true;" ^
  "    continue;" ^
  "  };" ^
  "  Write-Host ('top passage_id: ' + $passageId);" ^
  "  Write-Host ('top source: ' + $source);" ^
  "};" ^
  "if ($missing) { throw 'Session 4 wiki verification failed' };" ^
  "Write-Host 'verified: the exact Session 4 Annex III and Article 14 governance queries return cited evidence';"

exit /b %ERRORLEVEL%
