param(
    [string]$SourceDir = (Join-Path $PSScriptRoot "teststat-cli"),
    [string]$DistDir = (Join-Path $PSScriptRoot "dist"),
    [string]$ZipName = "TestStat-CLI.zip"
)

$ErrorActionPreference = "Stop"

$sourceRoot = (Resolve-Path -LiteralPath $SourceDir).ProviderPath
$outputDir = $DistDir
$outputZip = Join-Path $outputDir $ZipName
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("teststat-cli-package-" + [System.Guid]::NewGuid().ToString("N"))
$temporaryZip = Join-Path $outputDir ("." + [System.IO.Path]::GetFileNameWithoutExtension($ZipName) + ".tmp.zip")

$includeFiles = @(
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "MANIFEST.in",
    "config_sample.json",
    "test_stat_cli.py",
    "lists/list_sample.yaml"
)

$includeDirs = @(
    "utils",
    "assets"
)

$excludeDirNames = @(
    "__pycache__",
    ".pytest_cache"
)

$excludeFilePatterns = @(
    "*.pyc",
    "*.pyo"
)

function Copy-DistributionDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $sourcePath = Join-Path $sourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Container)) {
        return
    }

    Get-ChildItem -LiteralPath $sourcePath -Recurse -File | ForEach-Object {
        $relativeFile = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
        $pathParts = $relativeFile -split '[\\/]'

        if ($pathParts | Where-Object { $excludeDirNames -contains $_ }) {
            return
        }

        foreach ($pattern in $excludeFilePatterns) {
            if ($_.Name -like $pattern) {
                return
            }
        }

        $destinationPath = Join-Path $stagingRoot $relativeFile
        $destinationDir = Split-Path -Parent $destinationPath
        New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destinationPath -Force
    }
}

try {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    foreach ($file in $includeFiles) {
        $sourcePath = Join-Path $sourceRoot $file
        if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
            $destinationPath = Join-Path $stagingRoot $file
            $destinationDir = Split-Path -Parent $destinationPath
            New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
            Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
        }
    }

    foreach ($dir in $includeDirs) {
        Copy-DistributionDirectory -RelativePath $dir
    }

    if (Test-Path -LiteralPath $temporaryZip) {
        Remove-Item -LiteralPath $temporaryZip -Force
    }

    Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $temporaryZip -Force
    Move-Item -LiteralPath $temporaryZip -Destination $outputZip -Force

    Write-Host "Created: $outputZip"
}
finally {
    if (Test-Path -LiteralPath $temporaryZip) {
        Remove-Item -LiteralPath $temporaryZip -Force
    }
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
