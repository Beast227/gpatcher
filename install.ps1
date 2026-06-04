#requires -Version 5.1
<#
.SYNOPSIS
    Installs gpatcher to %LOCALAPPDATA%\gpatcher (Windows) or ~/.gpatcher (Unix) and adds it to the PATH.
.DESCRIPTION
    Copies all required files (scripts, binaries, wrapper scripts) to a permanent
    install directory and ensures it is on the user's PATH.
.PARAMETER InstallDir
    Override the default install location.
.PARAMETER Uninstall
    Remove gpatcher from the install directory and clean it from PATH.
#>
param(
    [string]$InstallDir = $null,
    [switch]$Uninstall
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

function Test-IsWindows {
    if ($null -ne (Get-Variable 'IsWindows' -ErrorAction SilentlyContinue)) {
        return $IsWindows
    }
    return $true
}

# Resolve default InstallDir if not provided
if (-not $InstallDir) {
    if (Test-IsWindows) {
        $InstallDir = Join-Path $env:LOCALAPPDATA 'gpatcher'
    } else {
        $InstallDir = Join-Path $HOME '.gpatcher'
    }
}

function Add-ToUserPath {
    param([string]$Dir)
    if (Test-IsWindows) {
        $current = [System.Environment]::GetEnvironmentVariable('Path', 'User')
        $entries = $current -split ';' | Where-Object { $_ -ne '' }
        if ($entries -contains $Dir) {
            Write-Host "  Already on PATH" -ForegroundColor Yellow
            return
        }
        $newPath = ($entries + $Dir) -join ';'
        [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        $env:Path = "$env:Path;$Dir"
        Write-Host "  Added to user PATH" -ForegroundColor Green
    } else {
        $rcFiles = @()
        $homeDir = $HOME
        $bashrc = Join-Path $homeDir '.bashrc'
        $zshrc = Join-Path $homeDir '.zshrc'
        $profile = Join-Path $homeDir '.profile'
        
        if (Test-Path -LiteralPath $bashrc) { $rcFiles += $bashrc }
        if (Test-Path -LiteralPath $zshrc) { $rcFiles += $zshrc }
        if ($rcFiles.Count -eq 0 -and (Test-Path -LiteralPath $profile)) { $rcFiles += $profile }
        if ($rcFiles.Count -eq 0) { $rcFiles += $bashrc }

        $exportLine = "export PATH=`"`$PATH:$Dir`""
        foreach ($rc in $rcFiles) {
            $content = ""
            if (Test-Path -LiteralPath $rc) {
                $content = [System.IO.File]::ReadAllText($rc)
            }
            if ($content -notlike "*$Dir*") {
                [System.IO.File]::AppendAllText($rc, "`n$exportLine`n")
                Write-Host "  Added to $rc" -ForegroundColor Green
            } else {
                Write-Host "  Already in $rc" -ForegroundColor Yellow
            }
        }
        $env:Path = "$env:Path:$Dir"
    }
}

function Remove-FromUserPath {
    param([string]$Dir)
    if (Test-IsWindows) {
        $current = [System.Environment]::GetEnvironmentVariable('Path', 'User')
        $entries = $current -split ';' | Where-Object { $_ -ne '' -and $_ -ne $Dir }
        $newPath = $entries -join ';'
        [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Write-Host "  Removed from user PATH" -ForegroundColor Green
    } else {
        $rcFiles = @()
        $homeDir = $HOME
        $bashrc = Join-Path $homeDir '.bashrc'
        $zshrc = Join-Path $homeDir '.zshrc'
        $profile = Join-Path $homeDir '.profile'
        
        if (Test-Path -LiteralPath $bashrc) { $rcFiles += $bashrc }
        if (Test-Path -LiteralPath $zshrc) { $rcFiles += $zshrc }
        if (Test-Path -LiteralPath $profile) { $rcFiles += $profile }

        foreach ($rc in $rcFiles) {
            if (Test-Path -LiteralPath $rc) {
                $lines = Get-Content -LiteralPath $rc
                $filtered = $lines | Where-Object { $_ -notlike "*$Dir*" }
                [System.IO.File]::WriteAllLines($rc, $filtered)
                Write-Host "  Cleaned up $rc" -ForegroundColor Green
            }
        }
    }
}

# --- Uninstall ---
if ($Uninstall) {
    Write-Host ""
    Write-Host "gpatcher uninstall" -ForegroundColor Cyan
    if (Test-Path -LiteralPath $InstallDir) {
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
        Write-Host "  Removed: $InstallDir" -ForegroundColor Green
    } else {
        Write-Host "  Not found: $InstallDir" -ForegroundColor Yellow
    }
    Remove-FromUserPath $InstallDir
    Write-Host "  Done!" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# --- Install ---
Write-Host ""
Write-Host "gpatcher installer" -ForegroundColor Cyan
Write-Host "  Source:  $PSScriptRoot" -ForegroundColor Gray
Write-Host "  Target:  $InstallDir" -ForegroundColor Gray
Write-Host ""

# Create install dir
if (Test-Path -LiteralPath $InstallDir) {
    Write-Host "  Removing old install..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Copy core files
$filesToCopy = New-Object System.Collections.Generic.List[string]
$filesToCopy.Add('gpatcher.ps1')
if (Test-IsWindows) {
    $filesToCopy.Add('gpatcher.cmd')
} else {
    $filesToCopy.Add('gpatcher')
}

foreach ($f in $filesToCopy) {
    $src = Join-Path $PSScriptRoot $f
    if (Test-Path -LiteralPath $src) {
        $dst = Join-Path $InstallDir $f
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host "  Copied: $f" -ForegroundColor Gray
        if ($f -eq 'gpatcher' -and -not (Test-IsWindows)) {
            & chmod +x $dst 2>$null
        }
    } else {
        Write-Host "  MISSING: $f" -ForegroundColor Red
        throw "Required file not found: $src"
    }
}

# Copy lib/
$libSrc = Join-Path $PSScriptRoot 'lib'
$libDst = Join-Path $InstallDir 'lib'
Copy-Item -LiteralPath $libSrc -Destination $libDst -Recurse -Force
Write-Host "  Copied: lib/ ($((Get-ChildItem $libDst -File).Count) files)" -ForegroundColor Gray

# Copy bin/
$binSrc = Join-Path $PSScriptRoot 'bin'
$binDst = Join-Path $InstallDir 'bin'
if (Test-Path -LiteralPath $binSrc) {
    Copy-Item -LiteralPath $binSrc -Destination $binDst -Recurse -Force
    # Set execution bit on Linux binaries
    if (-not (Test-IsWindows)) {
        Get-ChildItem -Path $binDst -File | ForEach-Object {
            & chmod +x $_.FullName 2>$null
        }
    }
    Write-Host "  Copied: bin/ ($((Get-ChildItem $binDst -File).Count) files)" -ForegroundColor Gray
} else {
    $script = if (Test-IsWindows) { "tools\fetch-hdiffpatch.ps1" } else { "tools/fetch-hdiffpatch.ps1" }
    Write-Host "  WARNING: bin/ not found -- run $script after install" -ForegroundColor Yellow
}

# Add to PATH
Write-Host ""
Add-ToUserPath $InstallDir

Write-Host ""
Write-Host "  Installed! Restart your terminal, then run:" -ForegroundColor Green
Write-Host "    gpatcher doctor" -ForegroundColor White
Write-Host "    gpatcher help" -ForegroundColor White
Write-Host ""
