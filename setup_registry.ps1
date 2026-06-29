param([string]$Action = "")

$dir     = $PSScriptRoot
$analyze = Join-Path $dir "aj_analyze.bat"
$ask     = Join-Path $dir "aj_ask.bat"

Write-Host "Script dir : $dir"
Write-Host ""

if (-not (Test-Path $analyze)) { Write-Error "Cannot find aj_analyze.bat"; exit 1 }
if (-not (Test-Path $ask))     { Write-Error "Cannot find aj_ask.bat";     exit 1 }

$analyzeCmd = 'cmd /k ""' + $analyze + '" "%1""'
$askCmd     = 'cmd /k ""' + $ask     + '" "%1""'

$ku    = [Microsoft.Win32.Registry]::CurrentUser
$store = "Software\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell"

# ── Clean up ALL previous Agent J entries ──────────────────
Write-Host "[1/4] Removing all old Agent J entries..."

$ku.DeleteSubKeyTree("Software\Classes\*\shell\AgentJ",          $false)
$ku.DeleteSubKeyTree("Software\Classes\*\shell\AgentJAsk",       $false)
$ku.DeleteSubKeyTree("Software\Classes\*\shell\AgentJAnalyze",   $false)
$ku.DeleteSubKeyTree("Software\Classes\*\shell\AgentJ_1Ask",     $false)
$ku.DeleteSubKeyTree("Software\Classes\*\shell\AgentJ_2Analyze", $false)
$ku.DeleteSubKeyTree("$store\AgentJAsk",                         $false)
$ku.DeleteSubKeyTree("$store\AgentJAnalyze",                     $false)

foreach ($ext in @("png","jpg","jpeg","webp","pdf")) {
    Remove-Item "HKCU:\Software\Classes\SystemFileAssociations\.$ext\shell\AgentJAnalyze" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "HKCU:\Software\Classes\SystemFileAssociations\.$ext\shell\AgentJ"        -Recurse -Force -ErrorAction SilentlyContinue
}

if ($Action -eq "/remove") {
    Write-Host "Removed all Agent J entries."
    Read-Host "Press Enter to close"
    exit
}

# ── Register two flat items under *\shell\ ─────────────────
# Key names start with "AgentJ_1" / "AgentJ_2" so they sort
# alphabetically adjacent in the context menu.
Write-Host "[2/4] Registering Ask and Analyze under *\shell..."

# -- Ask (item 1) --
$k = $ku.CreateSubKey("Software\Classes\*\shell\AgentJ_1Ask")
$k.SetValue("",         "Agent J  -  Ask")
$k.SetValue("MUIVerb",  "Agent J  -  Ask")
$k.SetValue("SeparatorBefore", 1)   # visual separator above
$c = $k.CreateSubKey("command")
$c.SetValue("", $askCmd)
$c.Close(); $k.Close()

# -- Analyze (item 2) --
$k = $ku.CreateSubKey("Software\Classes\*\shell\AgentJ_2Analyze")
$k.SetValue("",        "Agent J  -  Analyze")
$k.SetValue("MUIVerb", "Agent J  -  Analyze")
$k.SetValue("SeparatorAfter", 1)    # visual separator below
$c = $k.CreateSubKey("command")
$c.SetValue("", $analyzeCmd)
$c.Close(); $k.Close()

Write-Host "[3/4] Entries created."

# ── Restart Explorer ───────────────────────────────────────
Write-Host "[4/4] Restarting Explorer..."
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process explorer

# ── Verify ─────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Verify ==="
$v1 = $ku.OpenSubKey("Software\Classes\*\shell\AgentJ_1Ask\command")
$v2 = $ku.OpenSubKey("Software\Classes\*\shell\AgentJ_2Analyze\command")
if ($v1) { Write-Host "Ask cmd     : $($v1.GetValue(''))" } else { Write-Host "Ask     : NOT FOUND" }
if ($v2) { Write-Host "Analyze cmd : $($v2.GetValue(''))" } else { Write-Host "Analyze : NOT FOUND" }

Write-Host ""
Write-Host "Done. Right-click any file to see both Agent J items together."
Read-Host "Press Enter to close"
