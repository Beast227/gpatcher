#requires -Version 5.1
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$root     = Split-Path -Parent $PSScriptRoot
$cli      = Join-Path $root 'gpatcher.ps1'
$fixtures = Join-Path $root 'tests\fixtures'
$v1       = Join-Path $fixtures 'v1'
$v2       = Join-Path $fixtures 'v2'
$tmp      = Join-Path $root 'tests\tmp'

. (Join-Path $root 'lib\Common.ps1')
. (Join-Path $root 'lib\Walk.ps1')

function Reset-Fixtures {
    foreach ($p in @($v1, $v2, $tmp)) {
        if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Recurse -Force }
        New-Item -ItemType Directory -Path $p -Force | Out-Null
    }

    # Helper: write file, creating parent dirs.
    function Put-File {
        param([string]$Path, [string]$Text)
        $dir = Split-Path -Parent $Path
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($false))
    }

    # unchanged
    Put-File (Join-Path $v1 'static.txt') 'static content'
    Put-File (Join-Path $v2 'static.txt') 'static content'

    # modified small
    Put-File (Join-Path $v1 'data\config.ini') 'version=one'
    Put-File (Join-Path $v2 'data\config.ini') 'version=two and a bit longer'

    # added (v2 only)
    Put-File (Join-Path $v2 'new\added.txt') 'hello from v2'

    # deleted (v1 only)
    Put-File (Join-Path $v1 'old\removed.txt') 'goodbye'

    # files that should be excluded
    Put-File (Join-Path $v1 'data\Unity_Player.log') 'log file 1'
    Put-File (Join-Path $v2 'data\Unity_Player.log') 'log file 2'
    Put-File (Join-Path $v1 'saves\save001.sav') 'save content 1'
    Put-File (Join-Path $v2 'saves\save001.sav') 'save content 2'
    Put-File (Join-Path $v2 'new\custom.bak') 'backup file'
    Put-File (Join-Path $v1 'SaveScreenshots\shot001.png') 'screenshot content 1'
    Put-File (Join-Path $v2 'SaveScreenshots\shot001.png') 'screenshot content 2'

    # binary modified
    $size = 256KB
    $rand = New-Object System.Random 42
    $buf1 = New-Object byte[] $size
    $rand.NextBytes($buf1)
    [System.IO.File]::WriteAllBytes((Join-Path $v1 'big.bin'), $buf1)

    $buf2 = New-Object byte[] $size
    [Array]::Copy($buf1, $buf2, $size)
    $patch = New-Object byte[] 4096
    (New-Object System.Random 99).NextBytes($patch)
    [Array]::Copy($patch, 0, $buf2, 100000, 4096)
    [System.IO.File]::WriteAllBytes((Join-Path $v2 'big.bin'), $buf2)
}

function Hash-Dir {
    param([string]$Dir)
    $full = (Resolve-Path -LiteralPath $Dir).Path.TrimEnd('\','/')
    $files = Get-ChildItem -LiteralPath $full -Recurse -File | Sort-Object FullName
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        foreach ($f in $files) {
            $rel = $f.FullName.Substring($full.Length).TrimStart('\','/') -replace '\\','/'
            if (Test-IsExcluded -RelPath $rel -CustomExcludes @("*.bak")) {
                continue
            }
            $h = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLower()
            $line = "${rel}:$h`n"
            $b = [System.Text.Encoding]::UTF8.GetBytes($line)
            [void]$sha.TransformBlock($b, 0, $b.Length, $null, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
        [System.BitConverter]::ToString($sha.Hash).Replace('-','').ToLower()
    } finally {
        $sha.Dispose()
    }
}

$passed = 0
$failed = 0

function Run-Test {
    param([string]$Name, [scriptblock]$Body)
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    try {
        & $Body
        Write-Host "PASS: $Name" -ForegroundColor Green
        $script:passed++
    } catch {
        Write-Host "FAIL: $Name -- $_" -ForegroundColor Red
        $script:failed++
        throw
    }
}

Run-Test 'Setup fixtures' { Reset-Fixtures }

Run-Test 'Create patch' {
    & $cli create --old $v1 --new $v2 --game 'Test Game' --old-ver '1' --new-ver '2' --out $tmp --exclude "*.bak"
    if ($LASTEXITCODE -ne 0) { throw "create failed (exit $LASTEXITCODE)" }
}

Run-Test 'Verify exclusions in manifest' {
    $bundle = Get-ChildItem -LiteralPath $tmp -Filter '*.patch.zip' | Select-Object -First 1
    if (-not $bundle) { throw "No bundle produced in $tmp" }
    
    $staging = Join-Path $tmp 'manifest-check'
    if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($bundle.FullName, $staging)
    
    $manifestText = [System.IO.File]::ReadAllText((Join-Path $staging 'manifest.json'))
    Remove-Item $staging -Recurse -Force
    
    if ($manifestText -like '*Unity_Player.log*') {
        throw "Unity_Player.log was not excluded!"
    }
    if ($manifestText -like '*save001.sav*') {
        throw "save001.sav was not excluded!"
    }
    if ($manifestText -like '*custom.bak*') {
        throw "custom.bak was not excluded!"
    }
    if ($manifestText -like '*shot001.png*') {
        throw "SaveScreenshots file was not excluded!"
    }
    Write-Host "  Success: excluded files are not present in manifest." -ForegroundColor Green
}

$bundle = Get-ChildItem -LiteralPath $tmp -Filter '*.patch.zip' | Select-Object -First 1
if (-not $bundle) { throw "No bundle produced in $tmp" }
Write-Host "Bundle: $($bundle.FullName) ($($bundle.Length) bytes)"

$work = Join-Path $tmp 'work'
Run-Test 'Copy v1 to workspace' {
    Copy-Item -LiteralPath $v1 -Destination $work -Recurse -Force
}

Run-Test 'Apply patch (no-backup)' {
    & $cli apply --patch $bundle.FullName --target $work --no-backup
    if ($LASTEXITCODE -ne 0) { throw "apply failed (exit $LASTEXITCODE)" }
}

Run-Test 'Apply patch deletes backup by default' {
    $workD = Join-Path $tmp 'work-default'
    if (Test-Path $workD) { Remove-Item $workD -Recurse -Force }
    Copy-Item -LiteralPath $v1 -Destination $workD -Recurse -Force
    & $cli apply --patch $bundle.FullName --target $workD
    if ($LASTEXITCODE -ne 0) { throw "apply failed" }
    $bk = @(Get-ChildItem -LiteralPath $workD -Filter '.gpatcher-backup-*' -Directory -Force -ErrorAction SilentlyContinue)
    if ($bk.Count -ne 0) { throw "Backup folder was not deleted on success!" }
}

Run-Test 'Hash-compare workspace vs v2' {
    $hWork = Hash-Dir $work
    $hV2   = Hash-Dir $v2
    Write-Host "  work=$hWork"
    Write-Host "  v2  =$hV2"
    if ($hWork -ne $hV2) { throw "Tree hash mismatch after apply" }
}

Run-Test 'Restore from backup undoes apply' {
    $workR = Join-Path $tmp 'work-restore'
    Copy-Item -LiteralPath $v1 -Destination $workR -Recurse -Force

    & $cli apply --patch $bundle.FullName --target $workR --keep-backup
    if ($LASTEXITCODE -ne 0) { throw "apply (with backup) failed (exit $LASTEXITCODE)" }

    $bk = @(Get-ChildItem -LiteralPath $workR -Filter '.gpatcher-backup-*' -Directory -Force)
    if ($bk.Count -eq 0) { throw "no backup dir was created" }
    Write-Host "  backup: $($bk[0].Name)"

    & $cli restore --target $workR
    if ($LASTEXITCODE -ne 0) { throw "restore failed (exit $LASTEXITCODE)" }

    $bk2 = @(Get-ChildItem -LiteralPath $workR -Filter '.gpatcher-backup-*' -Directory -Force -ErrorAction SilentlyContinue)
    if ($bk2.Count -ne 0) { throw "backup dir should have been removed after restore" }

    $hWork = Hash-Dir $workR
    $hV1   = Hash-Dir $v1
    Write-Host "  work=$hWork"
    Write-Host "  v1  =$hV1"
    if ($hWork -ne $hV1) { throw "restored tree != v1" }
}

Run-Test 'Restore --keep-backup retains backup dir' {
    $workK = Join-Path $tmp 'work-keep'
    Copy-Item -LiteralPath $v1 -Destination $workK -Recurse -Force
    & $cli apply --patch $bundle.FullName --target $workK --keep-backup
    if ($LASTEXITCODE -ne 0) { throw "apply failed" }
    & $cli restore --target $workK --keep-backup
    if ($LASTEXITCODE -ne 0) { throw "restore --keep-backup failed" }
    $bk = @(Get-ChildItem -LiteralPath $workK -Filter '.gpatcher-backup-*' -Directory -Force)
    if ($bk.Count -eq 0) { throw "backup dir should have been retained" }
}

Run-Test 'Tampered install fails pre-flight' {
    $work2 = Join-Path $tmp 'work2'
    Copy-Item -LiteralPath $v1 -Destination $work2 -Recurse -Force
    [System.IO.File]::WriteAllText((Join-Path $work2 'static.txt'), 'tampered', [System.Text.UTF8Encoding]::new($false))
    & $cli apply --patch $bundle.FullName --target $work2 --no-backup
    if ($LASTEXITCODE -eq 0) { throw "apply on tampered install should have failed" }
    # ensure no mutation: static.txt still 'tampered'
    $cur = [System.IO.File]::ReadAllText((Join-Path $work2 'static.txt'))
    if ($cur -ne 'tampered') { throw "Tampered file mutated despite pre-flight failure" }
}

Run-Test 'Verify matches expected old snapshot' {
    & $cli verify --install $v1 --against $bundle.FullName
    if ($LASTEXITCODE -ne 0) { throw "verify should have succeeded (exit $LASTEXITCODE)" }
}

Run-Test 'Verify fails when modified' {
    $workV = Join-Path $tmp 'work-verify-fail'
    if (Test-Path $workV) { Remove-Item $workV -Recurse -Force }
    Copy-Item -LiteralPath $v1 -Destination $workV -Recurse -Force
    [System.IO.File]::WriteAllText((Join-Path $workV 'static.txt'), 'tampered', [System.Text.UTF8Encoding]::new($false))
    
    $out = & $cli verify --install $workV --against $bundle.FullName *>&1 | Out-String
    if ($LASTEXITCODE -eq 0) { throw "verify on tampered install should have failed" }
    if ($out -notmatch "1 file\(s\) differ from expected") {
        throw "Expected error output about 1 file differing, got: $out"
    }
}

Run-Test 'Update command in dev mode warns user' {
    # Store standard output, error, and information output (*>&1 captures Write-Host in PS 5+)
    $out = & $cli update *>&1 | Out-String
    if ($out -notmatch "Running from a Git repository clone") {
        throw "Expected Git clone warning, got: $out"
    }
}

Write-Host "`nResults: passed=$passed failed=$failed" -ForegroundColor $(if ($failed -eq 0) { 'Green' } else { 'Red' })
if ($failed -gt 0) { exit 1 } else { exit 0 }
