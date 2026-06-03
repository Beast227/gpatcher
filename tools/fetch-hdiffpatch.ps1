#requires -Version 5.1
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$root   = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $root 'bin'
if (-not (Test-Path -LiteralPath $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

Write-Host "Querying latest HDiffPatch release from GitHub..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$apiUrl  = 'https://api.github.com/repos/sisong/HDiffPatch/releases/latest'
$headers = @{ 'User-Agent' = 'popayarip-fetch' }
$rel     = Invoke-RestMethod -Uri $apiUrl -Headers $headers

$asset = $rel.assets | Where-Object {
    $_.name -match 'win.*64' -and $_.name -like '*.zip'
} | Select-Object -First 1

if (-not $asset) {
    throw "No win64 zip asset found in $($rel.tag_name)"
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

$hdiffz  = Get-ChildItem -LiteralPath $tmp -Recurse -Filter 'hdiffz.exe'  | Select-Object -First 1
$hpatchz = Get-ChildItem -LiteralPath $tmp -Recurse -Filter 'hpatchz.exe' | Select-Object -First 1
if (-not $hdiffz -or -not $hpatchz) {
    throw "hdiffz.exe / hpatchz.exe not found in extracted release zip"
}
Copy-Item -LiteralPath $hdiffz.FullName  -Destination (Join-Path $binDir 'hdiffz.exe')  -Force
Copy-Item -LiteralPath $hpatchz.FullName -Destination (Join-Path $binDir 'hpatchz.exe') -Force

Remove-Item -LiteralPath $tmp -Recurse -Force
Write-Host "OK -> $binDir"
