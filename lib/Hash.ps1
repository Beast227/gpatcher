function Get-FileSha256 {
    param([Parameter(Mandatory)][string]$Path)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        try {
            $hash = $sha.ComputeHash($fs)
        } finally {
            $fs.Dispose()
        }
    } finally {
        $sha.Dispose()
    }
    [System.BitConverter]::ToString($hash).Replace('-','').ToLowerInvariant()
}

function Get-MerkleRoot {
    param([Parameter(Mandatory)][hashtable]$PathHashMap)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $enc = [System.Text.Encoding]::UTF8
        foreach ($k in ($PathHashMap.Keys | Sort-Object)) {
            $line = "${k}:$($PathHashMap[$k])`n"
            $bytes = $enc.GetBytes($line)
            $null = $sha.TransformBlock($bytes, 0, $bytes.Length, $null, 0)
        }
        $null = $sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
        [System.BitConverter]::ToString($sha.Hash).Replace('-','').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}
