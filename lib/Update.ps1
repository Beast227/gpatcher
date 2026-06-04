function Invoke-Update {
    param(
        [switch]$Force
    )

    $toolRoot = Get-ToolRoot
    $isGitRepo = Test-Path (Join-Path $toolRoot '.git')
    if ($isGitRepo) {
        LogWarn "Running from a Git repository clone. Please use 'git pull' to update instead."
        return
    }

    LogInfo "Checking for updates..."
    $repo = 'Beast227/gpatcher'
    $apiUrl = "https://api.github.com/repos/$repo/releases/latest"
    $headers = @{ 'User-Agent' = 'gpatcher-update' }

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $rel = Invoke-RestMethod -Uri $apiUrl -Headers $headers
    } catch {
        throw "Failed to fetch latest release from GitHub: $_"
    }

    $latestTag = $rel.tag_name
    if (-not $latestTag) {
        throw "No release tag found on GitHub."
    }

    # Clean version strings to parse as [version]
    # e.g., 'v0.1' -> '0.1', 'v1.2.3-alpha' -> '1.2.3'
    $latestVerStr = $latestTag.TrimStart('v')
    if ($latestVerStr -match '^(\d+(?:\.\d+)+)') {
        $latestVerStr = $Matches[1]
    }

    $currentVerStr = $global:GPATCHER_VERSION
    if ($currentVerStr -match '^(\d+(?:\.\d+)+)') {
        $currentVerStr = $Matches[1]
    }

    try {
        $latestVer = [version]$latestVerStr
        $currentVer = [version]$currentVerStr
        $isNewer = $latestVer -gt $currentVer
    } catch {
        # Fallback to string comparison if version parsing fails
        $isNewer = $latestVerStr -ne $currentVerStr
    }

    if (-not $isNewer -and -not $Force) {
        LogOk "gpatcher is already up to date (v$global:GPATCHER_VERSION)."
        return
    }

    LogInfo "Updating gpatcher from v$global:GPATCHER_VERSION to $latestTag..."

    $pattern = if (Test-IsWindows) { 'win.*64' } else { 'linux.*64' }
    $asset = $rel.assets | Where-Object {
        $_.name -match $pattern -and $_.name -like '*.zip'
    } | Select-Object -First 1

    if (-not $asset) {
        $asset = $rel.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1
    }

    if (-not $asset) {
        throw "No zip asset found in release $latestTag"
    }

    $staging = New-TempDir 'gpatcher-update'
    try {
        $zipPath = Join-Path $staging 'gpatcher.zip'
        LogInfo "Downloading release asset: $($asset.name) ($(Format-Bytes $asset.size))"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing -Headers $headers

        LogInfo "Extracting update..."
        $extractDir = Join-Path $staging 'extract'
        New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
        Expand-Dir -ZipPath $zipPath -DestDir $extractDir

        LogInfo "Applying update..."
        # Copy core files
        $coreFiles = New-Object System.Collections.Generic.List[string]
        $coreFiles.Add('gpatcher.ps1')
        if (Test-IsWindows) {
            $coreFiles.Add('gpatcher.cmd')
        } else {
            $coreFiles.Add('gpatcher')
        }
        
        foreach ($f in $coreFiles) {
            $src = Join-Path $extractDir $f
            if (Test-Path -LiteralPath $src) {
                $dst = Join-Path $toolRoot $f
                Copy-Item -LiteralPath $src -Destination $dst -Force
                if ($f -eq 'gpatcher' -and -not (Test-IsWindows)) {
                    & chmod +x $dst 2>$null
                }
            }
        }

        # Copy install.ps1 if present
        $instSrc = Join-Path $extractDir 'install.ps1'
        if (Test-Path -LiteralPath $instSrc) {
            Copy-Item -LiteralPath $instSrc -Destination (Join-Path $toolRoot 'install.ps1') -Force
        }

        # Copy lib/
        $libSrc = Join-Path $extractDir 'lib'
        if (Test-Path -LiteralPath $libSrc) {
            $libDst = Join-Path $toolRoot 'lib'
            if (-not (Test-Path -LiteralPath $libDst)) {
                New-Item -ItemType Directory -Path $libDst -Force | Out-Null
            }
            Copy-Item -Path (Join-Path $libSrc '*') -Destination $libDst -Recurse -Force
        }

        # Copy bin/ (if present)
        $binSrc = Join-Path $extractDir 'bin'
        if (Test-Path -LiteralPath $binSrc) {
            $binDst = Join-Path $toolRoot 'bin'
            if (-not (Test-Path -LiteralPath $binDst)) {
                New-Item -ItemType Directory -Path $binDst -Force | Out-Null
            }
            Copy-Item -Path (Join-Path $binSrc '*') -Destination $binDst -Recurse -Force
            if (-not (Test-IsWindows)) {
                Get-ChildItem -Path $binDst -File | ForEach-Object {
                    & chmod +x $_.FullName 2>$null
                }
            }
        }

        LogOk "Successfully updated gpatcher to $latestTag!"
    } finally {
        Remove-PathSafe $staging
    }
}
