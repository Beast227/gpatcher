function Invoke-Update {
    param(
        [switch]$Force
    )

    $isGitRepo = (Test-Path (Join-Path $PSScriptRoot '.git')) -or (Test-Path (Join-Path (Split-Path $PSScriptRoot) '.git'))
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

    $currentVerStr = $GPATCHER_VERSION
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
        LogOk "gpatcher is already up to date (v$GPATCHER_VERSION)."
        return
    }

    LogInfo "Updating gpatcher from v$GPATCHER_VERSION to $latestTag..."

    $asset = $rel.assets | Where-Object {
        $_.name -match 'win.*64' -and $_.name -like '*.zip'
    } | Select-Object -First 1

    if (-not $asset) {
        # Fallback to any ZIP asset if win64 isn't explicitly in the name
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
        $coreFiles = @('gpatcher.ps1', 'gpatcher.cmd')
        foreach ($f in $coreFiles) {
            $src = Join-Path $extractDir $f
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $PSScriptRoot $f) -Force
            }
        }

        # Copy install.ps1 if present
        $instSrc = Join-Path $extractDir 'install.ps1'
        if (Test-Path -LiteralPath $instSrc) {
            Copy-Item -LiteralPath $instSrc -Destination (Join-Path $PSScriptRoot 'install.ps1') -Force
        }

        # Copy lib/
        $libSrc = Join-Path $extractDir 'lib'
        if (Test-Path -LiteralPath $libSrc) {
            Copy-Item -LiteralPath $libSrc -Destination (Join-Path $PSScriptRoot 'lib') -Recurse -Force
        }

        # Copy ui/ (if present)
        $uiSrc = Join-Path $extractDir 'ui'
        if (Test-Path -LiteralPath $uiSrc) {
            Copy-Item -LiteralPath $uiSrc -Destination (Join-Path $PSScriptRoot 'ui') -Recurse -Force
        }

        # Copy bin/ (if present)
        $binSrc = Join-Path $extractDir 'bin'
        if (Test-Path -LiteralPath $binSrc) {
            Copy-Item -LiteralPath $binSrc -Destination (Join-Path $PSScriptRoot 'bin') -Recurse -Force
        }

        LogOk "Successfully updated gpatcher to $latestTag!"
    } finally {
        Remove-PathSafe $staging
    }
}
