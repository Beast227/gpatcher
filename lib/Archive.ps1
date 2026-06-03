function Compress-Dir {
    param(
        [Parameter(Mandatory)][string]$SrcDir,
        [Parameter(Mandatory)][string]$ZipOut
    )
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $ZipOut) { Remove-Item -LiteralPath $ZipOut -Force }
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $SrcDir,
        $ZipOut,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )
}

function Expand-Dir {
    param(
        [Parameter(Mandatory)][string]$ZipPath,
        [Parameter(Mandatory)][string]$DestDir
    )
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (-not (Test-Path -LiteralPath $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $DestDir)
}
