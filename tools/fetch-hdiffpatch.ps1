#requires -Version 5.1
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$root   = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $root 'bin'
if (-not (Test-Path -LiteralPath $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

function Test-IsWindows {
    if ($null -ne (Get-Variable 'IsWindows' -ErrorAction SilentlyContinue)) {
        return $IsWindows
    }
    return $true
}

$isWin = Test-IsWindows

Write-Host "Querying latest HDiffPatch release from GitHub..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$apiUrl  = 'https://api.github.com/repos/sisong/HDiffPatch/releases/latest'
$headers = @{ 'User-Agent' = 'popayarip-fetch' }
$rel     = Invoke-RestMethod -Uri $apiUrl -Headers $headers

$pattern = if ($isWin) { 'win.*64' } else { 'linux.*64' }
$asset = $rel.assets | Where-Object {
    $_.name -match $pattern -and $_.name -like '*.zip'
} | Select-Object -First 1

if (-not $asset) {
    throw "No $pattern zip asset found in $($rel.tag_name)"
}

Write-Host "Release: $($rel.tag_name)"
Write-Host "Asset:   $($asset.name) ($($asset.size) bytes)"

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("hdp-" + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$zip = Join-Path $tmp 'hdp.zip'

Write-Host "Downloading..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing -Headers $headers

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $tmp)

$binExt = if ($isWin) { '.exe' } else { '' }
$hdiffzName = "hdiffz$binExt"
$hpatchzName = "hpatchz$binExt"

$hdiffz  = Get-ChildItem -LiteralPath $tmp -Recurse -Filter $hdiffzName  | Select-Object -First 1
$hpatchz = Get-ChildItem -LiteralPath $tmp -Recurse -Filter $hpatchzName | Select-Object -First 1
if (-not $hdiffz -or -not $hpatchz) {
    throw "$hdiffzName / $hpatchzName not found in extracted release zip"
}

$dstHdiffz = Join-Path $binDir $hdiffzName
$dstHpatchz = Join-Path $binDir $hpatchzName

Copy-Item -LiteralPath $hdiffz.FullName  -Destination $dstHdiffz  -Force
Copy-Item -LiteralPath $hpatchz.FullName -Destination $dstHpatchz -Force

if (-not $isWin) {
    & chmod +x $dstHdiffz 2>$null
    & chmod +x $dstHpatchz 2>$null
}

Remove-Item -LiteralPath $tmp -Recurse -Force
Write-Host "OK -> $binDir"
